"""Streaming annotated-video writer (fragmented MP4).

Why this exists
---------------
The annotated video must start playing in the browser *as soon as skeleton
mapping and tracking have produced the first frames* - not when analysis ends.

``cv2.VideoWriter`` cannot do that: it writes the MP4 index (the ``moov`` atom)
only when the file is closed, so until analysis finishes the file is unreadable
(the browser reports "moov atom not found"). Camera-side that is why the old
UI could only show a still JPEG every couple of chunks.

This writer pipes BGR frames to the ffmpeg binary bundled by ``imageio-ffmpeg``
and muxes them as a **fragmented** MP4:

* ``empty_moov`` - the index header is written up front, so the file is valid
  from the first byte rather than at the end.
* ``frag_keyframe`` - every keyframe starts a new self-contained fragment, so a
  reader that opens the file mid-recording can decode everything up to the last
  completed fragment.
* ``flush_packets`` - pushes each fragment to disk immediately instead of
  buffering it in ffmpeg until close.

The result is a file that grows and is playable throughout, which is what the
HTTP range-capable endpoint serves during processing.

Failure behaviour
-----------------
ffmpeg may be unavailable (a deployment without the bundled binary). The writer
therefore *degrades* rather than raising: if the process cannot be started, or
dies mid-run, it reports itself unusable and the pipeline falls back to the
in-loop preview JPEGs. A missing encoder must never fail an athlete's analysis.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import availability is environment dependent
    import imageio_ffmpeg

    _FFMPEG_EXE: Optional[str] = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001 - any import/binary problem disables streaming
    _FFMPEG_EXE = None


def ffmpeg_available() -> bool:
    """True when a usable ffmpeg binary was found at import time."""
    return _FFMPEG_EXE is not None


class StreamingVideoWriter:
    """Writes frames to a fragmented MP4 that is playable while being written.

    Usage mirrors ``cv2.VideoWriter``::

        writer = StreamingVideoWriter(path, fps, (w, h))
        writer.write(frame)
        writer.release()

    ``write`` is a no-op once the writer has failed, so callers need not guard
    every call.
    """

    def __init__(
        self,
        path: Path,
        fps: float,
        size: tuple,
        fragment_interval: int = 8,
        crf: int = 23,
        preset: str = "veryfast",
    ):
        """
        Args:
            path: Destination .mp4 path.
            fps: Playback frame rate of the written stream.
            size: ``(width, height)`` in pixels.
            fragment_interval: Frames per fragment (also the keyframe interval).
                Smaller = playback starts sooner, at a slightly higher bitrate.
            crf: x264 quality (lower = better/larger). 23 is the x264 default.
            preset: x264 speed/size trade-off. ``veryfast`` keeps encoding from
                becoming the pipeline's bottleneck.
        """
        self.path = Path(path)
        self.fps = float(fps) if fps and fps > 0 else 25.0
        self.size = (int(size[0]), int(size[1]))
        self.fragment_interval = max(1, int(fragment_interval))
        self.crf = int(crf)
        self.preset = preset
        self.frames_written = 0
        self._proc: Optional[subprocess.Popen] = None
        self._failed = not ffmpeg_available()
        self._error: Optional[str] = None

        if self._failed:
            self._error = "ffmpeg binary not available"
            logger.warning(
                "Streaming writer disabled: ffmpeg not found. "
                "Install 'imageio-ffmpeg' to enable live annotated playback."
            )
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._start()

    # -- lifecycle --------------------------------------------------------- #

    def _start(self) -> None:
        cmd = [
            _FFMPEG_EXE, "-y",
            "-loglevel", "error",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.size[0]}x{self.size[1]}",
            "-r", f"{self.fps:.6f}",
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            # yuv420p is required for broad browser support; x264 needs even
            # dimensions, so the caller must pass a conforming size.
            "-pix_fmt", "yuv420p",
            "-preset", self.preset,
            "-crf", str(self.crf),
            "-g", str(self.fragment_interval),
            "-sc_threshold", "0",
            # Emit each fragment as soon as it is complete, and push it out
            # rather than letting ffmpeg's own buffer hold it.
            "-flush_packets", "1",
            "-movflags",
            "+frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4",
            str(self.path),
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:  # noqa: BLE001 - never break analysis
            self._failed = True
            self._error = str(exc)
            logger.warning("Could not start streaming encoder: %s", exc)

    def is_usable(self) -> bool:
        """False once the encoder is missing/started-failed/died."""
        if self._failed or self._proc is None:
            return False
        return self._proc.poll() is None

    @property
    def error(self) -> Optional[str]:
        return self._error

    # -- writing ----------------------------------------------------------- #

    def write(self, frame: np.ndarray) -> bool:
        """Append one BGR frame. Returns True when it was handed to the encoder.

        A failure is latched: later calls become cheap no-ops.
        """
        if not self.is_usable():
            return False
        if frame is None or frame.size == 0:
            return False

        # x264 with yuv420p requires even width/height. The pipeline already
        # picks an even output size, but guard here so a stray odd frame cannot
        # kill the whole stream.
        h, w = frame.shape[:2]
        if (w, h) != self.size:
            try:
                import cv2

                frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
            except Exception as exc:  # noqa: BLE001
                self._fail(f"resize failed: {exc}")
                return False

        try:
            self._proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        except Exception as exc:  # noqa: BLE001 - broken pipe etc.
            self._fail(f"write failed: {exc}")
            return False

        self.frames_written += 1
        return True

    def _fail(self, message: str) -> None:
        self._failed = True
        self._error = message
        logger.warning("Streaming encoder failed: %s", message)

    def release(self) -> None:
        """Finalise the stream. Safe to call more than once."""
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(timeout=120)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing streaming encoder: %s", exc)
            try:
                proc.kill()
            except Exception:
                pass
            return

        # Surface encoder errors (e.g. bad pix_fmt) in the logs rather than
        # silently producing an empty file.
        try:
            if proc.stderr and proc.returncode not in (0, None):
                detail = proc.stderr.read().decode("utf-8", "replace").strip()
                if detail:
                    logger.warning("Encoder stderr: %s", detail)
        except Exception:
            pass
