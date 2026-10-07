from app.modules.video.router import _safe_filename


def test_safe_filename_rejects_path_traversal():
    assert _safe_filename("../../../etc/passwd") == "upload.mp4"
    assert _safe_filename("valid_video.mp4") == "valid_video.mp4"
    assert _safe_filename("video with spaces.mov") == "video with spaces.mov"
    assert _safe_filename("invalid_ext.txt") == "upload.mp4"


def test_safe_filename_accepts_new_extensions():
    assert _safe_filename("clip.webm") == "clip.webm"
    assert _safe_filename("clip.avi") == "clip.avi"
    assert _safe_filename("clip.mkv") == "clip.mkv"
    assert _safe_filename("clip.m4v") == "clip.m4v"
    assert _safe_filename("CLIP.WEBM") == "CLIP.WEBM"
    assert _safe_filename("my clip 01.MKV") == "my clip 01.MKV"


def test_safe_filename_rejects_evil_inputs():
    assert _safe_filename("../../evil.webm") == "evil.webm"
    assert _safe_filename("../../evil.exe") == "upload.mp4"
    assert _safe_filename("x.mp4.exe") == "upload.mp4"
    assert _safe_filename("x.webm.exe") == "upload.mp4"
    assert _safe_filename("no_extension") == "upload.mp4"
    assert _safe_filename("clip.txt") == "upload.mp4"
    assert _safe_filename("a" * 201 + ".mp4") == "upload.mp4"
    assert _safe_filename("semi;colon.mp4") == "upload.mp4"
