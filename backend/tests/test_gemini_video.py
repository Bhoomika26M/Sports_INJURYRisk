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

