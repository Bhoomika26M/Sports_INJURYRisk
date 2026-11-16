"""Unit tests for range-aware media responses.

Two behaviours matter here and both are load-bearing for live playback:

1. A normal range request returns exactly those bytes with a correct
   Content-Range, so a player can seek.
2. A range request against a file that is still GROWING (the annotated video
   mid-analysis) must succeed against the bytes that exist now, and an
   unsatisfiable range must return 416 rather than an empty or broken body -
   that 416 is what tells the player to retry as more data arrives.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.media import _parse_range, range_file_response


# --------------------------------------------------------------------------- #
# Range parsing
# --------------------------------------------------------------------------- #

def test_parse_full_range():
    assert _parse_range("bytes=0-99", 1000) == (0, 99)


def test_parse_open_ended_range_clamped_to_size():
    assert _parse_range("bytes=500-", 1000) == (500, 999)


def test_parse_suffix_range():
    assert _parse_range("bytes=-200", 1000) == (800, 999)


def test_parse_end_beyond_size_is_clamped():
    assert _parse_range("bytes=900-5000", 1000) == (900, 999)


def test_parse_start_beyond_size_is_invalid():
    assert _parse_range("bytes=2000-3000", 1000) is None


def test_parse_malformed_returns_none():
    assert _parse_range("items=0-10", 1000) is None
    assert _parse_range("bytes=abc-def", 1000) is None
    assert _parse_range("bytes=-", 1000) is None


# --------------------------------------------------------------------------- #
# HTTP behaviour
# --------------------------------------------------------------------------- #

@pytest.fixture
def media_app(tmp_path):
    """A tiny app exposing the helper over a fixed file."""
    payload = bytes(range(256)) * 4  # 1024 deterministic bytes
    target = tmp_path / "sample.mp4"
    target.write_bytes(payload)

    app = FastAPI()

    @app.get("/media")
    def media(request=None):  # request injected by FastAPI
        return range_file_response(target, media_type="video/mp4")

    # FastAPI needs the Request in the signature.
    from fastapi import Request

    @app.get("/media2")
    def media2(request: Request):
        return range_file_response(target, media_type="video/mp4", request=request)

    return TestClient(app), target, payload


def test_full_request_without_range_returns_200(media_app):
    client, _, payload = media_app
    r = client.get("/media2")
    assert r.status_code == 200
    assert r.content == payload
    assert r.headers["accept-ranges"] == "bytes"


def test_range_request_returns_206_and_exact_bytes(media_app):
    client, _, payload = media_app
    r = client.get("/media2", headers={"Range": "bytes=100-199"})
    assert r.status_code == 206
    assert r.content == payload[100:200]
    assert r.headers["content-range"] == f"bytes 100-199/{len(payload)}"
    assert r.headers["content-length"] == "100"


def test_open_ended_range_returns_rest_of_file(media_app):
    client, _, payload = media_app
    r = client.get("/media2", headers={"Range": "bytes=1000-"})
    assert r.status_code == 206
    assert r.content == payload[1000:]


def test_unsatisfiable_range_returns_416(media_app):
    """A player asking past the current end must be told to retry."""
    client, _, payload = media_app
    r = client.get("/media2", headers={"Range": f"bytes={len(payload) + 50}-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(payload)}"
    assert r.headers["accept-ranges"] == "bytes"


def test_growing_file_serves_only_bytes_that_exist(media_app):
    """Simulates live playback: the answer tracks the file's current size."""
    client, target, payload = media_app

    # Request everything; at this moment the file is full size.
    r = client.get("/media2", headers={"Range": "bytes=0-"})
    assert r.status_code == 206
    assert r.content == payload

    # Now pretend the file is only half-written, as it is mid-analysis.
    target.write_bytes(payload[:512])
    r = client.get("/media2", headers={"Range": "bytes=0-"})
    assert r.status_code == 206
    assert r.content == payload[:512]
    assert r.headers["content-range"].endswith("/512")

    # A request for bytes that do not exist yet is refused, not faked.
    r = client.get("/media2", headers={"Range": "bytes=900-999"})
    assert r.status_code == 416
