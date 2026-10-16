"""Offline gate for scripts/gemini_video.py. Gemini is faked with a stateful httpx.MockTransport that follows the
documented REST shapes (resumable upload -> poll -> interactions -> delete); ffmpeg is REAL, on synthetic clips.

What passing proves: preprocessing, request shapes, retries, fallback, cleanup, parsing, science-constraint scrubbing,
exit codes, and that the existing stack is untouched. What it cannot prove: Google's live behaviour. That is the
separate live gate in docs/GEMINI_VIDEO_PLAN.md (--list-models, then one real clip).
No Postgres, no GEMINI_API_KEY, no network. ffmpeg missing = a loud failure (zero skips), see gv.ffmpeg_bins().
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import sys
from fractions import Fraction
from pathlib import Path

import httpx
import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gemini_video as gv  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
KEY = "k-secret-123"
REAL_MAKE_CLIENT = gv.make_client


# --------------------------------------------------------------------------- helpers

def obs(**over):
    d = {"camera_view": "sagittal", "movement": "back squat", "reps_seen": 3,
         "joints": [{"joint": "knee", "side": "left", "visible": True, "note": "tracks over the toes"}],
         "knee_valgus": {"level": "not_assessable", "note": "side view"},
         "trunk_lean": {"level": "mild", "note": "slight forward lean"},
         "asymmetry": {"level": "none", "note": "even"},
         "quality": "good", "limitations": [], "summary": "Controlled squat."}
    d.update(over)
    return d


USAGE = {"input_tokens_by_modality": [{"modality": "text", "tokens": 700}, {"modality": "video", "tokens": 6720}],
         "total_input_tokens": 7420, "total_output_tokens": 310, "total_thought_tokens": 95, "total_tokens": 7825}


def reply(text, status="completed"):
    """The documented response shape: thought / processing steps may precede the model_output step."""
    return (200, {"status": status, "usage": USAGE, "steps": [
        {"type": "thought", "summary": [{"type": "text", "text": '{"junk": "must be ignored"}'}],
         "content": [{"type": "text", "text": '{"junk": "must be ignored"}'}]},
        {"type": "processing_call", "id": "c1"}, {"type": "processing_result", "call_id": "c1"},
        {"type": "model_output", "content": [{"type": "text", "text": text}]}]}, {})


def good(**over):
    return reply(json.dumps(obs(**over)))


class Fake:
    """Stateful fake of the Gemini endpoints we use. queue items: (status, json, headers) or an Exception to raise."""

    def __init__(self, states=("PROCESSING", "ACTIVE"), upload_host="generativelanguage.googleapis.com"):
        self.log, self.files, self.sleeps, self.queue = [], {}, [], []
        self.states, self.upload_host, self.model_status, self.model_pages = list(states), upload_host, {}, []

    def transport(self):
        return httpx.MockTransport(self.handle)

    def of(self, kind):
        return [r for k, r in self.log if k == kind]

    def kinds(self):
        return [k for k, _ in self.log]

    def models_called(self):
        return [json.loads(r.content)["model"] for r in self.of("interact")]

    def handle(self, req):
        path = req.url.path

        def rec(kind):
            self.log.append((kind, req))

        if req.method == "POST" and path == "/upload/v1beta/files":
            rec("start")
            return httpx.Response(200, json={}, headers={
                "x-goog-upload-url": f"https://{self.upload_host}/upload/v1beta/files/up1"})
        if req.method == "POST" and path.startswith("/upload/v1beta/files/"):
            rec("finalize")
            self.files["files/abc"] = req.content
            return httpx.Response(200, json={"file": {
                "name": "files/abc", "uri": "https://generativelanguage.googleapis.com/v1beta/files/abc",
                "mimeType": "video/mp4", "state": "PROCESSING"}})
        if req.method == "GET" and path == "/v1beta/files/abc":
            rec("poll")
            s = self.states.pop(0) if len(self.states) > 1 else self.states[0]
            return httpx.Response(200, json={"name": "files/abc", "state": s})
        if req.method == "DELETE" and path == "/v1beta/files/abc":
            rec("delete")
            self.files.pop("files/abc", None)
            return httpx.Response(200, json={})
        if req.method == "POST" and path == "/v1beta/interactions":
            rec("interact")
            model = json.loads(req.content)["model"]
            if model in self.model_status:
                return httpx.Response(self.model_status[model], json={"error": {"message": f"{model} unavailable"}})
            item = self.queue.pop(0) if self.queue else good()
            if isinstance(item, Exception):
                raise item
            status, body, headers = item
            return httpx.Response(status, json=body, headers=headers)
        if req.method == "GET" and path == "/v1beta/models":
            rec("models")
            i = int(req.url.params.get("pageToken", "0"))
            body = {"models": [{"name": n} for n in self.model_pages[i]]}
            if i + 1 < len(self.model_pages):
                body["nextPageToken"] = str(i + 1)
            return httpx.Response(200, json=body)
        raise AssertionError(f"unexpected request {req.method} {req.url}")


@pytest.fixture(scope="session")
def prepared(tmp_path_factory):
    return {"dir": tmp_path_factory.mktemp("prepared"), "done": {}}


@pytest.fixture
def fake(monkeypatch, prepared):
    """Fake Gemini + no sleeping. Preprocessing stays REAL ffmpeg but is encoded once per (clip, height) and copied,
    so the API-logic tests do not each pay for an encode. Direct preprocess tests do not use this fixture."""
    f = Fake()
    monkeypatch.setattr(gv, "_sleep", lambda s: f.sleeps.append(s))
    real = gv.preprocess

    def cached(src, out_dir, height=480):
        key = (str(src), height)
        if key not in prepared["done"]:
            prepared["done"][key] = real(src, tempfile.mkdtemp(dir=prepared["dir"]), height)
        clip, info = prepared["done"][key]
        dst = Path(out_dir) / "prepared.mp4"
        shutil.copy(clip, dst)
        return dst, dict(info)
    monkeypatch.setattr(gv, "preprocess", cached)
    return f


def run(fake, src, **kw):
    with gv.make_client(KEY, transport=fake.transport()) as c:
        return gv.analyze(src, c, **kw)


def synth(path, size="1280x720", dur=6, audio=True, rate=30, vcodec=("-c:v", "libx264", "-pix_fmt", "yuv420p")):
    ff, _ = gv.ffmpeg_bins()
    cmd = [ff, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration={dur}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}", "-c:a", "aac"]
    subprocess.run(cmd + list(vcodec) + [str(path)], check=True)
    return path


def streams(path):
    _, fp = gv.ffmpeg_bins()
    out = subprocess.run([fp, "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True)
    return json.loads(out.stdout)["streams"]


@pytest.fixture(scope="session")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("clips")
    return {
        "hd": synth(d / "athlete_jane_doe_squat.mp4"),
        "small": synth(d / "small.mp4", "320x240", 3, audio=False),
        "odd": synth(d / "odd.mp4", "640x479", 3, audio=False,
                     vcodec=("-c:v", "libx264", "-pix_fmt", "yuv444p")),
        "long": synth(d / "long.mp4", "320x180", 20, audio=False, rate=10),
        "short": synth(d / "short.mp4", "320x240", 0.5, audio=False),
    }


# --------------------------------------------------------------------------- guards: the stale / wrong-model traps

def test_omni_is_refused_before_anything_happens(monkeypatch, capsys):
    with pytest.raises(ValueError, match="generates"):
        gv.check_model("gemini-omni-1.1-flash")
    monkeypatch.setattr(gv, "get_key", lambda: pytest.fail("must refuse before reading the key"))
    assert gv.main(["x.mp4", "--model", "gemini-omni-1.1-flash"]) == 2
    assert "omni" in capsys.readouterr().err.lower()


def test_default_models_are_current_understanding_models():
    assert gv.MODELS and all(re.fullmatch(r"gemini-3\.\d+-flash(-lite)?", m) for m in gv.MODELS)


def test_schema_has_no_angle_score_or_probability_fields():
    keys = set()

    def walk(n):
        if isinstance(n, dict):
            keys.update(n.get("properties", {}))
            [walk(v) for v in n.values()]
        elif isinstance(n, list):
            [walk(v) for v in n]
    walk(gv.response_schema())
    assert keys, "walker found nothing"
    banned = ("angle", "degree", "probab", "percent", "score", "risk", "chance")
    assert not [k for k in keys if any(b in k for b in banned)]
    assert set(gv.response_schema()["properties"]["knee_valgus"]["properties"]) == {"level", "note"}


def test_schema_uses_only_keywords_gemini_structured_output_supports():
    s = json.dumps(gv.response_schema())
    for bad in ("$ref", "$defs", "maxLength", "pattern", '"default"'):
        assert bad not in s


@pytest.mark.parametrize("raw", ["knee valgus of 15\u00b0", "about 20 degrees of flexion", "a 90-degree bend",
                                 "15-20\u00b0 range", "4 deg", "12.5\u00ba"])
def test_scrub_removes_angles(raw):
    out = gv.scrub(raw)
    assert not re.search(r"\d", out), out
    assert "[angle omitted]" in out


def test_scrub_removes_injury_percentages_and_leaves_normal_text_alone():
    assert "[claim removed]" in gv.scrub("a 40% chance of injury is likely")
    assert "[claim removed]" in gv.scrub("injury risk looks 30% higher")
    plain = "Left knee tracks over the toes; no degeneration of form, three reps."
    assert gv.scrub(plain) == plain
    assert gv.scrub({"a": ["x 10\u00b0 y"], "n": 3}) == {"a": ["x [angle omitted] y"], "n": 3}


# --------------------------------------------------------------------------- the existing stack stays untouched

def test_app_does_not_know_about_gemini():
    hits = [p.name for p in (BACKEND / "app").rglob("*.py") if "gemini" in p.read_text(encoding="utf-8").lower()]
    assert not hits, hits


def test_module_is_isolated_from_app_and_the_sdk():
    src = (BACKEND / "scripts" / "gemini_video.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from|import)\s+app\b", src, re.M)
    assert not re.search(r"^\s*(from|import)\s+google\b", src, re.M)


def test_requirements_do_not_gain_the_google_sdk():
    reqs = (BACKEND / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "google-genai" not in reqs and "google-generativeai" not in reqs, (
        "google-genai needs websockets>=13 and pydantic>=2.12.5; this repo pins websockets==12.0 and "
        "pydantic==2.11.7. Bump those pins and re-run the WHOLE suite first, and log it in DECISIONS.md.")


# --------------------------------------------------------------------------- preprocessing (real ffmpeg)

def test_720p_clip_becomes_480p_silent_h264_with_frame_rate_untouched(clips, tmp_path):
    out, info = gv.preprocess(clips["hd"], tmp_path, 480)
    assert any(s["codec_type"] == "audio" for s in streams(clips["hd"])), "fixture should have audio"
    ss = streams(out)
    assert [s["codec_type"] for s in ss] == ["video"]
    v = ss[0]
    assert (v["width"], v["height"], v["codec_name"]) == (854, 480, "h264")
    assert abs(float(Fraction(v["r_frame_rate"])) - 30) < 0.5, "ffmpeg must not decimate: Gemini samples server-side"
    assert abs(info["duration"] - 6) < 0.3
    assert 0 < info["out_bytes"] < info["src_bytes"]


def test_small_clip_is_never_upscaled(clips, tmp_path):
    out, _ = gv.preprocess(clips["small"], tmp_path, 480)
    v = streams(out)[0]
    assert (v["width"], v["height"]) == (320, 240)


def test_odd_height_source_still_encodes_to_even_sizes(clips, tmp_path):
    out, _ = gv.preprocess(clips["odd"], tmp_path, 480)
    v = streams(out)[0]
    assert v["height"] == 478 and v["width"] % 2 == 0
    assert v["pix_fmt"] == "yuv420p", "a 4:4:4 source must come out in the format every decoder accepts"


def test_missing_garbage_and_too_short_inputs_fail_cleanly(clips, tmp_path):
    with pytest.raises(FileNotFoundError):
        gv.preprocess(tmp_path / "nope.mp4", tmp_path)
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"this is not a video" * 50)
    with pytest.raises(gv.AnalysisError, match="could not read"):
        gv.preprocess(junk, tmp_path)
    with pytest.raises(gv.AnalysisError, match="shorter than 1 second"):
        gv.preprocess(clips["short"], tmp_path)
    for bad in (479, 100):
        with pytest.raises(ValueError):
            gv.preprocess(clips["hd"], tmp_path, bad)


def test_ffmpeg_command_never_decimates_fps_or_keeps_audio():
    cmd = gv.ffmpeg_cmd("ffmpeg", "a.mp4", "b.mp4", 480)
    assert "-an" in cmd and "-r" not in cmd
    vf = cmd[cmd.index("-vf") + 1]
    assert "fps" not in vf
    assert "trunc(ih/2)*2" in vf and vf.startswith("scale=-2:"), "x264 on some ffmpeg builds rejects odd sizes"


# --------------------------------------------------------------------------- chunk windows

def test_windows_known_values():
    assert gv.windows(20, 8) == [(0, 8), (7, 15), (14, 20)]
    assert gv.windows(5, None) == [None] and gv.windows(8.5, 8) == [None]
    with pytest.raises(ValueError):
        gv.windows(60, 1.0)


def test_windows_use_whole_numbers_where_they_can():
    assert json.dumps(gv.windows(20, 8)) == "[[0, 8], [7, 15], [14, 20]]"
    assert json.dumps(gv.windows(20.5, 8)) == "[[0, 8], [7, 15], [14, 20.5]]"


def test_offsets_on_the_wire_are_duration_strings_with_an_s_suffix():
    """API reference: start_offset/end_offset are strings like "7.5s"; bare numbers are what a raw-REST call must not send."""
    f = {"uri": "u"}
    assert gv.video_part(f, (7, 15), 4.0, "high")["processing"] == {
        "type": "static", "fps": 4.0, "start_offset": "7s", "end_offset": "15s"}
    assert gv.video_part(f, (14, 20.5), 4.0, "high")["processing"]["end_offset"] == "20.5s"
    assert "start_offset" not in gv.video_part(f, None, 4.0, "high")["processing"]


@given(duration=st.floats(1.0, 3600), chunk=st.floats(2.0, 120))
@settings(max_examples=300, deadline=None)
def test_windows_cover_the_clip_in_order_with_exact_overlap(duration, chunk):
    w = gv.windows(duration, chunk)
    if w == [None]:
        assert duration <= chunk + gv.OVERLAP_S
        return
    tol = 0.011  # windows are rounded to 0.01 s
    assert w[0][0] == 0 and abs(w[-1][1] - duration) < tol
    for s, e in w:
        assert 0 < e - s <= chunk + gv.OVERLAP_S + tol
    for (s1, e1), (s2, e2) in zip(w, w[1:]):
        assert s2 > s1 and abs((e1 - s2) - gv.OVERLAP_S) < tol
    assert w[-1][1] - w[-1][0] >= gv.OVERLAP_S - tol, "no sliver tail chunk"


# --------------------------------------------------------------------------- the request contract

def test_happy_path_follows_the_documented_flow_and_request_shapes(fake, clips):
    rep = run(fake, clips["hd"], movement="squat")
    assert fake.kinds() == ["start", "finalize", "poll", "poll", "interact", "delete"]
    assert all(r.headers["x-goog-api-key"] == KEY for _, r in fake.log)
    assert not any(KEY in str(r.url) for _, r in fake.log), "key belongs in a header, never a URL"

    start, fin = fake.of("start")[0], fake.of("finalize")[0]
    assert start.headers["x-goog-upload-protocol"] == "resumable" and start.headers["x-goog-upload-command"] == "start"
    assert start.headers["x-goog-upload-header-content-type"] == "video/mp4"
    assert start.headers["x-goog-upload-header-content-length"] == str(len(fin.content))
    assert json.loads(start.content) == {"file": {"display_name": "clip"}}
    assert b"jane" not in start.content.lower(), "the athlete's filename must not reach Google"
    assert fin.headers["x-goog-upload-command"] == "upload, finalize" and fin.headers["x-goog-upload-offset"] == "0"
    assert b"ftyp" in fin.content[:16] and len(fin.content) == rep["settings"]["prepared"]["out_bytes"]

    body = json.loads(fake.of("interact")[0].content)
    assert set(body) == {"model", "input", "response_format", "store"}, "only fields documented for the Interactions API"
    assert body["store"] is False, "interactions are stored by default (1 day free, 55 paid); athlete footage must not be"
    assert body["model"] == "gemini-3.8-flash"
    assert body["input"][0] == {"type": "video", "uri": "https://generativelanguage.googleapis.com/v1beta/files/abc",
                                "mime_type": "video/mp4", "resolution": "high",
                                "processing": {"type": "static", "fps": 4.0}}
    assert body["input"][1]["type"] == "text" and len(body["input"]) == 2, "text goes AFTER the video"
    prompt = body["input"][1]["text"].lower()
    assert "labelled this movement: squat" in prompt and "never state joint angles" in prompt
    assert body["response_format"] == {"type": "text", "mime_type": "application/json", "schema": gv.response_schema()}

    assert fake.files == {}, "uploaded file must be deleted"
    assert rep["model"] == "gemini-3.8-flash" and rep["confidence"] == "qualitative"
    assert rep["overall"]["quality"] == "good" and rep["disclaimer"] == gv.DISCLAIMER


def test_prompt_makes_each_flag_depend_on_the_camera_view():
    p = gv.build_prompt().lower()
    assert "pure side view" in p and "both legs" in p and "sideways tilt" in p and "forward flexion" in p


def test_media_resolution_default_omits_the_field(fake, clips):
    run(fake, clips["hd"], media_resolution="default")
    assert "resolution" not in json.loads(fake.of("interact")[0].content)["input"][0]


def test_custom_settings_reach_the_request(fake, clips):
    run(fake, clips["hd"], fps=2.5, media_resolution="low", models=["gemini-3.5-flash-lite"])
    body = json.loads(fake.of("interact")[0].content)
    assert body["model"] == "gemini-3.5-flash-lite"
    assert body["input"][0]["resolution"] == "low" and body["input"][0]["processing"]["fps"] == 2.5


# --------------------------------------------------------------------------- upload / processing hardening

def test_failed_file_state_raises_and_still_deletes(fake, clips):
    fake.states = ["FAILED"]
    with pytest.raises(gv.AnalysisError, match="FAILED"):
        run(fake, clips["hd"])
    assert "interact" not in fake.kinds() and fake.files == {} and fake.kinds()[-1] == "delete"


def test_file_that_never_activates_times_out_and_deletes(fake, clips, monkeypatch):
    monkeypatch.setattr(gv, "POLL_MAX", 3)
    fake.states = ["PROCESSING"]
    with pytest.raises(gv.AnalysisError, match="timed out"):
        run(fake, clips["hd"])
    assert fake.kinds().count("poll") == 3 and fake.files == {}


def test_upload_url_off_google_is_refused_so_the_key_cannot_leak(clips):
    f = Fake(upload_host="evil.example.com")
    with gv.make_client(KEY, transport=f.transport()) as c, pytest.raises(gv.AnalysisError, match="Google upload URL"):
        gv.upload(c, clips["small"])
    assert f.kinds() == ["start"]


# --------------------------------------------------------------------------- retries and error handling

def test_429_is_retried_honouring_retry_after_then_succeeds(fake, clips):
    fake.states = ["ACTIVE"]
    fake.queue = [(429, {"error": {"message": "slow down"}}, {"retry-after": "7"}),
                  (429, {"error": {"message": "slow down"}}, {}), good()]
    rep = run(fake, clips["hd"], models=["gemini-3.8-flash"])  # retries/backoff apply to the last (here: only) candidate
    assert fake.sleeps[1:] == [7.0, 2] and fake.kinds().count("interact") == 3 and rep["overall"]


def test_5xx_exhausts_retries_then_raises_and_cleans_up(fake, clips):
    fake.states = ["ACTIVE"]
    fake.queue = [(503, {"error": {"message": "overloaded"}}, {})] * 10
    with pytest.raises(gv.ApiError) as e:
        run(fake, clips["hd"], models=["gemini-3.8-flash"])
    assert e.value.status == 503 and fake.kinds().count("interact") == 5 and fake.files == {}


def test_bad_request_is_not_retried_and_the_key_never_leaks_into_errors(fake, clips):
    fake.queue = [(400, {"error": {"message": "fps out of range"}}, {})]
    with pytest.raises(gv.ApiError) as e:
        run(fake, clips["hd"])
    assert e.value.status == 400 and "fps out of range" in str(e.value) and KEY not in str(e.value)
    assert fake.kinds().count("interact") == 1, "a 400 must not walk the fallback chain"
    assert fake.files == {}


def test_network_blip_is_retried(fake, clips):
    fake.states = ["ACTIVE"]
    fake.queue = [httpx.ConnectError("boom"), good()]
    assert run(fake, clips["hd"])["overall"] and fake.kinds().count("interact") == 2


# --------------------------------------------------------------------------- model availability

def test_falls_back_when_the_first_model_is_missing(fake, clips):
    fake.model_status = {"gemini-3.8-flash": 404}
    rep = run(fake, clips["hd"])
    assert rep["model"] == gv.MODELS[1] and fake.models_called() == gv.MODELS[:2]


def test_later_chunks_stick_to_the_model_that_worked(fake, clips):
    fake.model_status = {"gemini-3.8-flash": 404}
    rep = run(fake, clips["long"], chunk_seconds=8)
    assert len(rep["chunks"]) == 3
    assert fake.models_called() == [gv.MODELS[0]] + [gv.MODELS[1]] * 3


def test_overloaded_and_over_quota_models_are_skipped_at_once_when_alternatives_exist(fake, clips, capsys):
    """Live probe on a free key: 3.8 -> 503 (high demand), 3.6 -> 429 (quota). That must not mean 15 s+ of backoff each."""
    fake.states = ["ACTIVE"]
    fake.model_status = {gv.MODELS[0]: 503, gv.MODELS[1]: 429, gv.MODELS[2]: 503}
    rep = run(fake, clips["hd"])
    assert rep["model"] == gv.MODELS[3] and fake.models_called() == gv.MODELS[:4], "each tried exactly once"
    assert fake.sleeps == [gv.POLL_S], "no backoff while a fallback is still available"
    err = capsys.readouterr().err
    assert f"{gv.MODELS[0]} unavailable (503)" in err and f"trying {gv.MODELS[1]}" in err


def test_the_last_candidate_still_gets_full_backoff(fake, clips):
    fake.states = ["ACTIVE"]
    first, last = gv.MODELS[:2]
    fake.model_status = {first: 503}
    fake.queue = [(503, {"error": {"message": "busy"}}, {})] * 2 + [good()]
    rep = run(fake, clips["hd"], models=[first, last])
    assert rep["model"] == last and fake.models_called() == [first] + [last] * 3 and fake.sleeps[1:] == [1, 2]


def test_pinned_model_never_falls_back(fake, clips):
    fake.model_status = {"gemini-3.8-flash": 404}
    with pytest.raises(gv.ApiError, match="404"):
        run(fake, clips["hd"], models=["gemini-3.8-flash"])
    assert fake.models_called() == ["gemini-3.8-flash"]


def test_every_model_unavailable_raises_after_trying_all(fake, clips):
    fake.model_status = {m: 404 for m in gv.MODELS}
    with pytest.raises(gv.ApiError, match="404"):
        run(fake, clips["hd"])
    assert fake.models_called() == gv.MODELS and fake.files == {}


def test_list_models_paginates_and_strips_the_prefix():
    f = Fake()
    f.model_pages = [["models/gemini-3.8-flash", "models/gemini-omni-1.1-flash"], ["models/gemini-3.5-flash-lite"]]
    with gv.make_client(KEY, transport=f.transport()) as c:
        assert gv.list_models(c) == ["gemini-3.8-flash", "gemini-omni-1.1-flash", "gemini-3.5-flash-lite"]


# --------------------------------------------------------------------------- chunking end to end

def test_chunking_uploads_once_and_sends_one_window_per_chunk(fake, clips):
    fake.states = ["ACTIVE"]
    fake.queue = [good(quality="good", knee_valgus={"level": "none", "note": "ok"}),
                  good(quality="poor", knee_valgus={"level": "marked", "note": "collapse"},
                       trunk_lean={"level": "marked", "note": "lean"}),
                  good(quality="not_assessable", knee_valgus={"level": "not_assessable", "note": "?"})]
    rep = run(fake, clips["long"], chunk_seconds=8)
    assert fake.kinds().count("finalize") == 1 and fake.kinds().count("interact") == 3
    sent = [json.loads(r.content)["input"][0]["processing"] for r in fake.of("interact")]
    assert [(p["start_offset"], p["end_offset"]) for p in sent] == [
        (f"{c['window'][0]}s", f"{c['window'][1]}s") for c in rep["chunks"]]
    assert [c["window"][0] for c in rep["chunks"]] == [0, 7, 14]
    assert rep["overall"] == {"quality": "poor", "knee_valgus": "marked", "trunk_lean": "marked",
                              "asymmetry": "none", "chunks_ok": 3, "chunks_total": 3}


def test_too_many_chunks_is_refused_before_any_upload(fake, clips):
    with pytest.raises(gv.AnalysisError, match="too many"):
        run(fake, clips["long"], chunk_seconds=1.5)
    assert fake.log == []


# --------------------------------------------------------------------------- response handling

def test_a_bad_chunk_is_recorded_and_the_others_survive(fake, clips):
    fake.states = ["ACTIVE"]
    fake.queue = [good(), reply("this is not json"), reply(json.dumps(obs(quality="excellent")))]
    rep = run(fake, clips["long"], chunk_seconds=8)
    assert [bool(c["analysis"]) for c in rep["chunks"]] == [True, False, False]
    assert all(c["error"] for c in rep["chunks"][1:]) and rep["overall"]["chunks_ok"] == 1


def test_empty_blocked_response_is_a_chunk_error_not_a_crash(fake, clips):
    fake.queue = [(200, {"status": "failed", "steps": []}, {})]
    rep = run(fake, clips["hd"])
    assert rep["chunks"][0]["analysis"] is None and "empty response" in rep["chunks"][0]["error"]
    assert rep["overall"] is None


def test_empty_response_error_includes_googles_error_list(fake, clips):
    fake.queue = [(200, {"status": "failed", "steps": [], "errors": [{"code": "x", "message": "blocked by safety"}]}, {})]
    assert "blocked by safety" in run(fake, clips["hd"])["chunks"][0]["error"]


def test_only_model_output_text_is_parsed(fake, clips):
    rep = run(fake, clips["hd"])  # default reply carries a junk-JSON thought step before model_output
    assert rep["chunks"][0]["analysis"]["movement"] == "back squat"


def test_model_prose_cannot_smuggle_precision_through_the_error_text(fake, clips):
    for text in ["The valgus angle is 15\u00b0 and the chance of injury is 40%",
                 json.dumps(obs(quality="poor, about 15\u00b0 of valgus"))]:
        fake.queue = [reply(text)]
        err = run(fake, clips["hd"])["chunks"][0]["error"]
        assert "schema" in err and "15" not in err and "40" not in err and "\u00b0" not in err, err


def test_fabricated_precision_never_reaches_the_report(fake, clips):
    fake.queue = [good(knee_valgus={"level": "marked", "note": "valgus of about 15\u00b0 on the left"},
                       summary="A 40% chance of injury is likely.", limitations=["20 degrees of error"])]
    text = json.dumps(run(fake, clips["hd"]))
    assert "15\u00b0" not in text and "40%" not in text and "20 degrees" not in text
    assert "[angle omitted]" in text and "[claim removed]" in text


# --------------------------------------------------------------------------- CLI

def test_key_comes_from_dotenv_but_the_real_environment_wins(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GEMINI_API_KEY= from-dotenv \n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.delenv("GEMINI_API_KEY")  # so teardown removes whatever load_dotenv sets
    assert gv.get_key() == "from-dotenv"
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert gv.get_key() == "from-env"


def patch_client(monkeypatch, fake):
    monkeypatch.setattr(gv, "get_key", lambda: KEY)
    monkeypatch.setattr(gv, "make_client", lambda key: REAL_MAKE_CLIENT(key, transport=fake.transport()))


def test_cli_dry_run_needs_no_key_and_no_network(clips, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gv, "get_key", lambda: pytest.fail("dry-run must not read the key"))
    monkeypatch.setattr(gv, "make_client", lambda *a, **k: pytest.fail("dry-run must not build a client"))
    assert gv.main([str(clips["long"]), "--dry-run", "--chunk-seconds", "8", "--fps", "2"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["first_request_video_part"]["processing"] == {"type": "static", "fps": 2.0, "start_offset": "0s",
                                                             "end_offset": "8s"}
    assert len(out["windows"]) == 3 and out["prepared"]["height"] == 180
    assert (tmp_path / "gemini_out" / "long.prepared.mp4").stat().st_size > 0


def test_cli_without_a_key_exits_2_with_instructions(clips, monkeypatch, capsys):
    monkeypatch.setattr(gv, "get_key", lambda: "")
    assert gv.main([str(clips["hd"])]) == 2
    err = capsys.readouterr().err
    assert "GEMINI_API_KEY" in err and "aistudio.google.com" in err and "Traceback" not in err


@pytest.mark.parametrize("argv", [["nope.mp4"], ["--fps", "0"], ["--fps", "50"], ["--height", "479"],
                                  ["--chunk-seconds", "1"]])
def test_cli_bad_input_exits_2_before_any_network(argv, clips, monkeypatch, capsys, fake):
    patch_client(monkeypatch, fake)
    argv = argv if argv[0] == "nope.mp4" else [str(clips["small"]), *argv]  # a real clip: the flag itself must fail
    assert gv.main(argv) == 2 and fake.log == []
    assert "error:" in capsys.readouterr().err


def test_cli_full_run_writes_a_valid_report_and_cleans_up(clips, tmp_path, monkeypatch, capsys, fake):
    monkeypatch.chdir(tmp_path)
    patch_client(monkeypatch, fake)
    assert gv.main([str(clips["long"]), "--chunk-seconds", "8", "--movement", "squat"]) == 0
    rep = json.loads((tmp_path / "gemini_out" / "long.json").read_text(encoding="utf-8"))
    assert rep["method"] == "gemini_video_observation" and len(rep["chunks"]) == 3 and rep["overall"]
    keys = set()

    def walk(n):
        if isinstance(n, dict):
            keys.update(n)
            [walk(v) for v in n.values()]
        elif isinstance(n, list):
            [walk(v) for v in n]
    walk(rep)
    assert not [k for k in keys if any(b in k for b in ("angle", "degree", "probab", "percent", "score"))]
    assert fake.files == {}
    assert gv.DISCLAIMER in capsys.readouterr().out


def test_cli_exits_1_when_every_chunk_fails_but_still_writes_the_report(clips, tmp_path, monkeypatch, fake):
    monkeypatch.chdir(tmp_path)
    patch_client(monkeypatch, fake)
    fake.queue = [reply("garbage")] * 3
    assert gv.main([str(clips["long"]), "--chunk-seconds", "8"]) == 1
    assert json.loads((tmp_path / "gemini_out" / "long.json").read_text())["overall"] is None


def test_cli_api_failure_exits_1_and_still_deletes_the_upload(clips, monkeypatch, capsys, fake):
    patch_client(monkeypatch, fake)
    fake.queue = [(400, {"error": {"message": "API key not valid"}}, {})]
    assert gv.main([str(clips["hd"])]) == 1
    assert "API key not valid" in capsys.readouterr().err and fake.files == {}


def test_cli_list_models_probes_each_visible_candidate_once_and_flags_omni(monkeypatch, capsys, fake):
    patch_client(monkeypatch, fake)
    fake.model_pages = [["models/gemini-3.8-flash", "models/gemini-3.6-flash", "models/gemini-omni-1.1-flash",
                         "models/gemini-3.3-pro"]]
    fake.model_status = {"gemini-3.6-flash": 429}
    assert gv.main(["--list-models"]) == 0
    out = capsys.readouterr().out
    assert "ok   gemini-3.8-flash" in out
    assert re.search(r"FAIL gemini-3\.6-flash\s+\(.*429", out)
    assert re.search(r"FAIL gemini-3\.5-flash-lite\s+\(not visible", out)
    assert "gemini-omni-1.1-flash" in out and "GENERATION" in out and "gemini-3.3-pro" in out
    assert fake.models_called() == ["gemini-3.8-flash", "gemini-3.6-flash"], "one probe per visible candidate, no retry"
    body = json.loads(fake.of("interact")[0].content)
    assert set(body) == {"model", "input"} and "video" not in json.dumps(body)


def test_cli_list_models_exits_1_when_no_candidate_answers(monkeypatch, capsys, fake):
    patch_client(monkeypatch, fake)
    fake.model_pages = [["models/gemini-3.8-flash", "models/gemini-omni-1.1-flash"]]
    fake.model_status = {"gemini-3.8-flash": 403}
    assert gv.main(["--list-models"]) == 1
    assert "--model" in capsys.readouterr().err


def test_a_probe_that_gets_an_empty_answer_is_not_ok(monkeypatch, capsys, fake):
    patch_client(monkeypatch, fake)
    fake.model_pages = [["models/gemini-3.8-flash"]]
    fake.queue = [(200, {"status": "completed", "steps": []}, {})]
    assert gv.main(["--list-models"]) == 1
    assert "answered with nothing" in capsys.readouterr().out


def test_usage_is_kept_and_summarised_so_fps_and_resolution_can_be_verified(clips, tmp_path, monkeypatch, capsys, fake):
    monkeypatch.chdir(tmp_path)
    patch_client(monkeypatch, fake)
    assert gv.main([str(clips["hd"])]) == 0
    rep = json.loads((tmp_path / "gemini_out" / f"{clips['hd'].stem}.json").read_text(encoding="utf-8"))
    assert rep["chunks"][0]["usage"] == USAGE
    out = capsys.readouterr().out
    assert "video=6720" in out and re.search(r"~2[78]\d per requested frame", out)


def test_terminal_report_explains_not_assessable_with_the_notes_and_limitations(clips, tmp_path, monkeypatch, capsys,
                                                                                 fake):
    monkeypatch.chdir(tmp_path)
    patch_client(monkeypatch, fake)
    fake.queue = [good(knee_valgus={"level": "not_assessable", "note": "pure side view"}, limitations=["far leg hidden"])]
    assert gv.main([str(clips["hd"])]) == 0
    out = capsys.readouterr().out
    assert "knee_valgus: not_assessable - pure side view" in out and "limitations: far leg hidden" in out
