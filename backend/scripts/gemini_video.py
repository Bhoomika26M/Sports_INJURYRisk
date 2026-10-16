"""Standalone Gemini video-observation check. NOT part of the app: no DB, no imports from app/, never feeds scoring.

    python backend/scripts/gemini_video.py clip.mp4 [--fps 4] [--height 480] [--chunk-seconds 8] [--movement squat]
    python backend/scripts/gemini_video.py clip.mp4 --dry-run     # preprocess + show the request: no key, no network
    python backend/scripts/gemini_video.py --list-models          # which candidate models actually answer for your key

Needs GEMINI_API_KEY (env or .env) from https://aistudio.google.com/apikey. Plan, decisions, live-check gate:
docs/GEMINI_VIDEO_PLAN.md. Talks to the REST API with httpx (already pinned) because the google-genai SDK needs
websockets>=13 / pydantic>=2.12.5, which this repo pins lower.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

API = "https://generativelanguage.googleapis.com"
# Understanding models only. gemini-omni-* GENERATES/edits video (it cannot analyse it); 1.5/2.0 are shut down; 2.5 is
# restricted to existing users. Tried in order, failing fast, when a model is missing/forbidden/out of quota/overloaded.
MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
          "gemini-3.1-flash-lite"]
OVERLAP_S = 1.0  # chunk windows overlap so a rep that straddles a cut is whole in at least one chunk
MAX_CHUNKS = 30
POLL_S, POLL_MAX = 2.0, 90
RETRY_STATUS = {429, 500, 502, 503, 504}
FALLBACK_STATUS = {403, 404, 429, 500, 502, 503, 504}
QUALITY_ORDER = ["good", "fair", "poor"]
LEVEL_ORDER = ["none", "mild", "marked"]
DISCLAIMER = (
    "Qualitative observations by an AI model watching a downscaled video. Not measurements, not a diagnosis, not an "
    "injury prediction. Knee valgus is a visual flag only. Kept apart from the platform's pose pipeline: do not feed "
    "this into baselines or risk scores."
)
_sleep = time.sleep  # tests replace this


class AnalysisError(RuntimeError):
    pass


class ApiError(AnalysisError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Gemini API {status}: {message}")
        self.status = status


# --------------------------------------------------------------------------- schema + prompt

Level = Literal["none", "mild", "marked", "not_assessable"]


class Joint(BaseModel):
    joint: Literal["hip", "knee", "ankle", "shoulder", "trunk"]
    side: Literal["left", "right", "center"]
    visible: bool
    note: str


class Flag(BaseModel):
    level: Level
    note: str


class Observation(BaseModel):
    """What the model must return per clip window. Deliberately no angle, score or probability field."""
    camera_view: Literal["sagittal", "frontal", "oblique", "unclear"]
    movement: str
    reps_seen: int = Field(ge=0)
    joints: list[Joint]
    knee_valgus: Flag
    trunk_lean: Flag
    asymmetry: Flag
    quality: Literal["good", "fair", "poor", "not_assessable"]
    limitations: list[str]
    summary: str


def _inline(node, defs):
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline(defs[node["$ref"].split("/")[-1]], defs)
        return {k: _inline(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline(v, defs) for v in node]
    return node


def response_schema() -> dict:
    """Pydantic schema with $ref/$defs inlined: Gemini accepts only a JSON-Schema subset."""
    s = Observation.model_json_schema()
    return _inline(s, s.get("$defs", {}))


PROMPT = """You are a sports biomechanist reviewing one short clip of an athlete. Describe ONLY what is visible.

{hint}

Report, for hips, knees, ankles, shoulders (left and right where visible) and the trunk: whether the joint is visible
and a short note on how it moves. If a joint is out of frame or occluded, set visible=false and do not guess.

Judge three things as none | mild | marked | not_assessable, each with a one-sentence note, and only as far as the
camera view allows (say in the note which view limits you):
- knee_valgus: inward collapse of a knee during loading. Needs a front, back or oblique view; from a pure side view
  answer not_assessable. This is a visual flag only.
- trunk_lean: forward flexion needs a side or oblique view; sideways tilt needs a front or back view. Judge only the
  one your view shows.
- asymmetry: visible weight shift or unequal knee bend between left and right. Needs BOTH legs clearly visible; if one
  leg is hidden or out of frame answer not_assessable.
Then give quality good | fair | poor | not_assessable for the movement as a whole, the camera view, the number of full
repetitions seen (your best count; say in limitations if unsure) and any limitations (occlusion, clothing, distance,
low resolution, clip cut off).

Hard rules: never state joint angles or degrees. Never give a probability, percentage or prediction of injury.
Never diagnose. If the clip does not show a clear athletic movement, use not_assessable and say why in limitations.
Reply with JSON only."""

_DEG = re.compile(
    r"\d+(?:\.\d+)?(?:\s*[-\u2013]\s*\d+(?:\.\d+)?)?\s*-?\s*(?:\u00b0|\u00ba|deg(?:rees?)?\b)", re.I)
_CLAIM = re.compile(r"\d+\s*%[^.]{0,40}injur|injur[^.]{0,40}\d+\s*%", re.I)


def scrub(node):
    """Free text may not carry fabricated precision (SCIENCE_CONSTRAINTS: no valgus angle, no injury probability)."""
    if isinstance(node, str):
        return _CLAIM.sub("[claim removed]", _DEG.sub("[angle omitted]", node))
    if isinstance(node, list):
        return [scrub(v) for v in node]
    if isinstance(node, dict):
        return {k: scrub(v) for k, v in node.items()}
    return node


def build_prompt(movement: str | None = None, kinematic_context: str | None = None) -> str:
    hints = []
    if movement:
        hints.append(f"The uploader labelled this movement: {movement[:40]}. If the video clearly shows something else, say so in limitations instead of forcing the label.")
    else:
        hints.append("The movement is not labelled; identify it from the video.")
    if kinematic_context:
        hints.append(f"Pose tracking kinematic metrics: {kinematic_context[:300]}. Calibrate your qualitative observations and joint notes using these kinematic measurements.")
    return PROMPT.format(hint=" ".join(hints))



# --------------------------------------------------------------------------- ffmpeg

def ffmpeg_bins() -> tuple[str, str]:
    """System ffmpeg+ffprobe, else the static-ffmpeg bundle already in requirements.txt (downloads once)."""
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not (ff and fp):
        try:
            from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
            ff, fp = get_or_fetch_platform_executables_else_raise()[:2]
        except Exception as e:  # noqa: BLE001 - any failure here means "no ffmpeg"
            raise AnalysisError(f"ffmpeg/ffprobe not found ({e}); install ffmpeg or `pip install static-ffmpeg`") from e
    return ff, fp


def ffmpeg_cmd(ffmpeg: str, src, dst, height: int) -> list[str]:
    # Even sizes only (x264), never upscale, no audio (tokens for nothing). The frame rate is NOT touched: Gemini
    # samples frames server-side (processing.fps), so decimating here would silently cap what --fps can deliver.
    vf = f"scale=-2:min({height}\\,trunc(ih/2)*2)"
    return [ffmpeg, "-y", "-v", "error", "-i", str(src), "-an", "-vf", vf, "-c:v", "libx264", "-preset", "fast",
            "-crf", "28", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]


def probe(ffprobe: str, path) -> dict:
    r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        return {"width": j["streams"][0]["width"], "height": j["streams"][0]["height"],
                "duration": float(j["format"]["duration"])}
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise AnalysisError("no readable video stream in that file") from e


def preprocess(src, out_dir, height: int = 480) -> tuple[Path, dict]:
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"no such file: {src}")
    if height < 120 or height % 2:
        raise ValueError("height must be even and >= 120")
    ffmpeg, ffprobe = ffmpeg_bins()
    dst = Path(out_dir) / "prepared.mp4"
    r = subprocess.run(ffmpeg_cmd(ffmpeg, src, dst, height), capture_output=True, text=True)
    if r.returncode != 0 or not dst.is_file():
        raise AnalysisError("ffmpeg could not read that video: " + r.stderr.strip()[-300:])
    info = probe(ffprobe, dst)
    if info["duration"] < 1.0:
        raise AnalysisError("clip is shorter than 1 second")
    return dst, {**info, "src_bytes": src.stat().st_size, "out_bytes": dst.stat().st_size}


def _n(x: float):
    x = round(x, 2)
    return int(x) if x == int(x) else x


def windows(duration: float, chunk_s: float | None = None, overlap: float = OVERLAP_S) -> list[tuple[float, float] | None]:
    """[None] = whole video. Otherwise overlapping (start, end) seconds covering [0, duration]."""
    if not chunk_s or duration <= chunk_s + overlap:
        return [None]
    if chunk_s <= overlap:
        raise ValueError("--chunk-seconds must be larger than the 1 s overlap")
    out, start = [], 0.0
    while True:
        end = start + chunk_s
        if duration - end < overlap:  # absorb a tail shorter than the overlap instead of making a sliver chunk
            end = duration
        out.append((_n(start), _n(end)))
        if end >= duration:
            return out
        start = end - overlap


# --------------------------------------------------------------------------- Gemini REST

def make_client(key: str, transport=None) -> httpx.Client:
    return httpx.Client(headers={"x-goog-api-key": key}, timeout=httpx.Timeout(300, connect=15), transport=transport)


def _msg(r: httpx.Response) -> str:
    try:
        return str(r.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return r.text[:200]


def _wait(r: httpx.Response, attempt: int) -> float:
    try:
        return min(float(r.headers["retry-after"]), 30)
    except (KeyError, ValueError):
        return min(2 ** attempt, 30)


def _call(client: httpx.Client, method: str, url: str, attempts: int = 5, retry_http: bool = True,
          **kw) -> httpx.Response:
    for attempt in range(attempts):
        try:
            r = client.request(method, url, **kw)
        except httpx.TransportError as e:
            if attempt == attempts - 1:
                raise AnalysisError(f"network error talking to Gemini: {type(e).__name__}") from e
            _sleep(min(2 ** attempt, 30))
            continue
        if r.status_code in RETRY_STATUS and retry_http and attempt < attempts - 1:
            _sleep(_wait(r, attempt))
            continue
        if r.is_error:
            raise ApiError(r.status_code, _msg(r))
        return r
    raise AnalysisError("unreachable")  # pragma: no cover


def upload(client: httpx.Client, path) -> dict:
    data = Path(path).read_bytes()
    r = _call(client, "POST", f"{API}/upload/v1beta/files", headers={
        "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(len(data)), "X-Goog-Upload-Header-Content-Type": "video/mp4",
    }, json={"file": {"display_name": "clip"}})  # constant name: never send the athlete's filename to Google
    url = r.headers.get("x-goog-upload-url", "")
    if not httpx.URL(url).host.endswith(".googleapis.com"):  # the API key rides on this request: Google hosts only
        raise AnalysisError("upload start returned no usable Google upload URL")
    r = _call(client, "POST", url, headers={"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"},
              content=data)
    f = r.json().get("file") or {}
    if not (f.get("name") and f.get("uri")):
        raise AnalysisError("upload finished but Gemini returned no file name/uri")
    return f


def wait_active(client: httpx.Client, f: dict) -> dict:
    for _ in range(POLL_MAX):
        if f.get("state") == "ACTIVE":
            return f
        if f.get("state") == "FAILED":
            raise AnalysisError("Gemini could not process the video (file state FAILED)")
        _sleep(POLL_S)
        f = {**f, **_call(client, "GET", f"{API}/v1beta/{f['name']}").json()}
    raise AnalysisError("timed out waiting for Gemini to process the video")


def delete(client: httpx.Client, name: str) -> None:
    try:
        ok = client.delete(f"{API}/v1beta/{name}").status_code < 400
    except httpx.HTTPError:
        ok = False
    if not ok:  # uploaded files also expire on Google's side
        print(f"warning: could not delete uploaded file {name}", file=sys.stderr)


def video_part(f: dict, window, fps: float, media_resolution: str) -> dict:
    proc: dict = {"type": "static", "fps": fps}
    if window:
        proc |= {"start_offset": f"{window[0]}s", "end_offset": f"{window[1]}s"}  # API reference: strings with an 's' suffix
    part = {"type": "video", "uri": f["uri"], "mime_type": "video/mp4", "processing": proc}
    if media_resolution != "default":  # "default" omits the field: the escape hatch if the server rejects it
        part["resolution"] = media_resolution
    return part


def _output_text(d: dict) -> str:
    return "".join(c.get("text", "") for s in d.get("steps", []) if s.get("type") == "model_output"
                   for c in s.get("content", []) if c.get("type") == "text")


def interact(client: httpx.Client, model: str, part: dict, prompt: str, retry_http: bool = True) -> tuple[str, dict | None]:
    body = {"model": model, "input": [part, {"type": "text", "text": prompt}],  # text AFTER the video, per the docs
            "response_format": {"type": "text", "mime_type": "application/json", "schema": response_schema()},
            "store": False}  # interactions are stored by default (1 day free, 55 days paid): do not keep athlete footage
    d = _call(client, "POST", f"{API}/v1beta/interactions", retry_http=retry_http, json=body).json()
    text = _output_text(d).strip()
    if not text:
        raise AnalysisError(f"empty response from Gemini (status={d.get('status')}, errors={str(d.get('errors'))[:150]}): "
                            "blocked or no output")
    return text, d.get("usage")


def list_models(client: httpx.Client) -> list[str]:
    names, token = [], None
    for _ in range(20):
        params = {"pageSize": 200, **({"pageToken": token} if token else {})}
        j = _call(client, "GET", f"{API}/v1beta/models", params=params).json()
        names += [m["name"].removeprefix("models/") for m in j.get("models", [])]
        token = j.get("nextPageToken")
        if not token:
            break
    return names


def probe_model(client: httpx.Client, model: str) -> str:
    """One tiny text request, no retries: 'ok' or why not. Visibility in ListModels says nothing about quota."""
    try:
        r = _call(client, "POST", f"{API}/v1beta/interactions", attempts=1,
                  json={"model": model, "input": "Reply with the single word: ok"})
    except ApiError as e:
        return str(e)[:100]
    return "ok" if _output_text(r.json()).strip() else "answered with nothing"


# --------------------------------------------------------------------------- orchestration

def check_model(m: str) -> None:
    if "omni" in m.lower():
        raise ValueError("gemini-omni-* generates/edits video and cannot analyse it. Use a gemini-3.x flash model "
                         "(run --list-models).")


def _worst(values, order):
    seen = [v for v in values if v in order]
    return max(seen, key=order.index) if seen else "not_assessable"


def rollup(chunks: list[dict]) -> dict | None:
    ok = [c["analysis"] for c in chunks if c["analysis"]]
    if not ok:
        return None
    return {"quality": _worst([o["quality"] for o in ok], QUALITY_ORDER),
            **{k: _worst([o[k]["level"] for o in ok], LEVEL_ORDER) for k in ("knee_valgus", "trunk_lean", "asymmetry")},
            "chunks_ok": len(ok), "chunks_total": len(chunks)}


def _why(e: Exception) -> str:
    if isinstance(e, ValidationError):  # pydantic's default text echoes the model's words (input_value=...)
        e = "reply failed the schema: " + "; ".join(
            f"{'.'.join(map(str, x['loc'])) or 'reply'}: {x['msg']}"
            for x in e.errors(include_input=False, include_url=False))
    return str(e)[:300]


def _one_chunk(client, f, window, candidates, fps, media_resolution, prompt):
    part = video_part(f, window, fps, media_resolution)
    for i, m in enumerate(candidates):
        last = i == len(candidates) - 1
        try:  # while alternatives remain, a busy/over-quota model is skipped at once; only the last one gets backoff
            text, usage = interact(client, m, part, prompt, retry_http=last)
        except ApiError as e:
            if e.status in FALLBACK_STATUS and not last:
                print(f"note: {m} unavailable ({e.status}); trying {candidates[i + 1]}", file=sys.stderr)
                continue
            raise
        return m, Observation.model_validate_json(text), usage
    raise AnalysisError("no model candidates")  # pragma: no cover


def analyze(src, client: httpx.Client, *, height=480, fps=4.0, media_resolution="high", chunk_seconds=None,
            models=None, movement=None, kinematic_context=None) -> dict:
    candidates = list(models or MODELS)
    for m in candidates:
        check_model(m)
    prompt = build_prompt(movement, kinematic_context)
    with tempfile.TemporaryDirectory() as td:
        clip, info = preprocess(src, td, height)
        wins = windows(info["duration"], chunk_seconds)
        if len(wins) > MAX_CHUNKS:
            raise AnalysisError(f"{len(wins)} chunks is too many (max {MAX_CHUNKS}); raise --chunk-seconds")
        f = upload(client, clip)
        chunks, used = [], None
        try:
            f = wait_active(client, f)
            for w in wins:
                try:
                    used, obs, usage = _one_chunk(client, f, w, [used] if used else candidates, fps, media_resolution, prompt)
                    chunks.append({"window": w, "analysis": scrub(obs.model_dump()), "error": None, "usage": usage})
                except ApiError:
                    raise  # auth / quota / bad request: the next chunk would fail the same way
                except (AnalysisError, ValidationError) as e:
                    chunks.append({"window": w, "analysis": None, "error": _why(e), "usage": None})
        finally:
            delete(client, f["name"])
    return {"method": "gemini_video_observation", "confidence": "qualitative", "model": used, "source": Path(src).name,
            "settings": {"height": height, "fps": fps, "media_resolution": media_resolution,
                         "chunk_seconds": chunk_seconds, "prepared": info},
            "chunks": chunks, "overall": rollup(chunks), "disclaimer": DISCLAIMER}


def get_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        from dotenv import find_dotenv, load_dotenv  # python-dotenv ships with the pinned pydantic-settings
        load_dotenv(find_dotenv(usecwd=True))
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            repo_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            if os.path.exists(repo_root_env):
                load_dotenv(repo_root_env)
                key = os.environ.get("GEMINI_API_KEY", "").strip()
    except ImportError:
        pass
    return key


def _usage_line(u, seconds: float, fps: float) -> str:
    if not isinstance(u, dict):
        return ""
    video = sum(m.get("tokens", 0) for m in u.get("input_tokens_by_modality") or [] if m.get("modality") == "video")
    per_frame = f", ~{video / (seconds * fps):.0f} per requested frame (high ~280, low ~70)" if video and seconds else ""
    return (f"tokens: input={u.get('total_input_tokens')} video={video}{per_frame} "
            f"output={u.get('total_output_tokens')} thought={u.get('total_thought_tokens')}")


def print_report(rep: dict) -> None:
    print(f"\nmodel: {rep['model']}   source: {rep['source']}")
    st = rep["settings"]
    for c in rep["chunks"]:
        w = f"{c['window'][0]}s-{c['window'][1]}s" if c["window"] else "whole clip"
        a = c["analysis"]
        if not a:
            print(f"  [{w}] FAILED: {c['error']}")
            continue
        print(f"  [{w}] {a['movement']} ({a['camera_view']} view, {a['reps_seen']} reps) quality={a['quality']}")
        for k in ("knee_valgus", "trunk_lean", "asymmetry"):
            print(f"      {k}: {a[k]['level']} - {a[k]['note']}")
        if a["limitations"]:
            print("      limitations: " + "; ".join(a["limitations"]))
        print(f"      {a['summary']}")
        secs = (c["window"][1] - c["window"][0]) if c["window"] else st["prepared"]["duration"]
        if line := _usage_line(c.get("usage"), secs, st["fps"]):
            print(f"      {line}")
    if rep["overall"]:
        print(f"overall (worst case across chunks): {rep['overall']}")
    print("\n" + DISCLAIMER)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # Windows consoles choke on non-cp1252 characters in model text
    ap = argparse.ArgumentParser(description="Gemini video observation (standalone; see docs/GEMINI_VIDEO_PLAN.md)")
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--fps", type=float, default=4.0, help="frames/second Gemini samples (server-side; default 4)")
    ap.add_argument("--height", type=int, default=480, help="downscale target height in px (default 480)")
    ap.add_argument("--media-resolution", choices=["low", "medium", "high", "default"], default="high",
                    help="tokens per frame; high ~280, low ~70; default = let Gemini choose")
    ap.add_argument("--chunk-seconds", type=float, help="split long clips into overlapping windows of this length")
    ap.add_argument("--movement", help="what the uploader says it is, e.g. squat (a hint, not an override)")
    ap.add_argument("--model", help="pin one model (no fallback)")
    ap.add_argument("--out", help="JSON report path (default gemini_out/<clip>.json)")
    ap.add_argument("--dry-run", action="store_true", help="preprocess + print the request; no key, no network")
    ap.add_argument("--list-models", action="store_true")
    a = ap.parse_args(argv)
    try:
        if not 0.1 <= a.fps <= 30:
            raise ValueError("--fps must be between 0.1 and 30")
        models = [a.model] if a.model else MODELS
        for m in models:
            check_model(m)
        if a.list_models:
            return _cmd_list(models)
        if not a.clip:
            ap.error("a clip path is required (or --list-models)")
        if a.dry_run:
            return _cmd_dry_run(a)
        key = get_key()
        if not key:
            print("GEMINI_API_KEY is not set. Create a free key at https://aistudio.google.com/apikey and put "
                  "GEMINI_API_KEY=... in .env (or the environment).", file=sys.stderr)
            return 2
        with make_client(key) as client:
            rep = analyze(a.clip, client, height=a.height, fps=a.fps, media_resolution=a.media_resolution,
                          chunk_seconds=a.chunk_seconds, models=models, movement=a.movement)
    except (ValueError, FileNotFoundError) as e:  # bad input: nothing was sent anywhere
        print(f"error: {e}", file=sys.stderr)
        return 2
    except AnalysisError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out = Path(a.out or Path("gemini_out") / f"{Path(a.clip).stem}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print_report(rep)
    print(f"\nwrote {out}")
    return 0 if rep["overall"] else 1


def _cmd_list(models: list[str]) -> int:
    key = get_key()
    if not key:
        print("GEMINI_API_KEY is not set (https://aistudio.google.com/apikey)", file=sys.stderr)
        return 2
    try:
        with make_client(key) as client:
            names = list_models(client)
            results = {m: probe_model(client, m) if m in names else "not visible to this key" for m in models}
    except AnalysisError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print("Default candidates, in the order they are tried (each got one 1-token test request):")
    for m, r in results.items():
        print(f"  {'ok  ' if r == 'ok' else 'FAIL'} {m}" + ("" if r == "ok" else f"  ({r})"))
    other = sorted(n for n in names if n.startswith("gemini-") and n not in models)
    print("Other gemini models visible (omni = video GENERATION, not usable here):\n  " + "\n  ".join(other))
    if "ok" not in results.values():
        print("None of the default candidates answered: pass --model <a name from the list above>.", file=sys.stderr)
        return 1
    return 0


def _cmd_dry_run(a) -> int:
    with tempfile.TemporaryDirectory() as td:
        clip, info = preprocess(a.clip, td, a.height)
        wins = windows(info["duration"], a.chunk_seconds)
        keep = Path("gemini_out") / f"{Path(a.clip).stem}.prepared.mp4"
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(clip, keep)
    part = video_part({"uri": "<uploaded file uri>"}, wins[0], a.fps, a.media_resolution)
    print(json.dumps({"prepared": info, "windows": wins, "first_request_video_part": part,
                      "models_in_order": [a.model] if a.model else MODELS, "prepared_clip": str(keep)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
