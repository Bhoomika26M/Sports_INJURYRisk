import pytest
import re
from app.modules.videos.router import _safe_filename

def test_safe_filename_rejects_path_traversal():
    assert _safe_filename("../../../etc/passwd") == "upload.mp4"
    assert _safe_filename("valid_video.mp4") == "valid_video.mp4"
    assert _safe_filename("video with spaces.mov") == "video with spaces.mov"
    assert _safe_filename("invalid_ext.txt") == "upload.mp4"
