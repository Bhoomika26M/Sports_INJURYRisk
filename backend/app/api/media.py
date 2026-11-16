"""Range-aware file responses for media.

Why
---
A plain ``FileResponse`` advertises no ``Accept-Ranges`` and ignores the
``Range`` header. Media elements rely on ranges for two things:

* **Progressive playback.** A fragmented MP4 is playable while it is still
  being written, but only if the player can request the bytes that exist so
  far and re-request the growing tail. Without range support the browser
  fetches the whole (partial) file once and stops.
* **Seeking.** Scrubbing to a timestamp requires fetching a byte range.

This module returns a ``206 Partial Content`` response with an accurate
``Content-Range`` and a correct byte window, and falls back to a full ``200``
when no range is requested or the range is unsatisfiable.

Safety notes
------------
* The size is read from disk at request time, so a *growing* file reports its
  current length rather than a stale one.
* An open-ended range (``bytes=N-``) is clamped to the bytes that exist right
  now. A player asking for the whole tail of a file still being written gets
  today's bytes, then asks again - which is exactly how live playback works.
* Reading is capped per request so one client cannot force the server to buffer
  a multi-gigabyte file in memory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import Request
from fastapi.responses import FileResponse, Response, StreamingResponse

# bytes=start-end | bytes=start- | bytes=-suffix
_RANGE_RE = re.compile(r"bytes=(?P<start>\d*)-(?P<end>\d*)")

# Upper bound on a single range response, to bound memory use.
MAX_CHUNK = 8 * 1024 * 1024  # 8 MiB


def _parse_range(header: str, file_size: int) -> Optional[tuple]:
    """Return ``(start, end_inclusive)`` or None if the range is unusable."""
    match = _RANGE_RE.fullmatch(header.strip())
    if not match:
        return None

    start_raw = match.group("start")
    end_raw = match.group("end")

    if start_raw == "" and end_raw == "":
        return None

    if start_raw == "":
        # Suffix range: the last N bytes.
        suffix = int(end_raw)
        if suffix <= 0:
            return None
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        start = int(start_raw)
        if end_raw == "":
            end = file_size - 1
        else:
            end = min(int(end_raw), file_size - 1)

    if start > end or start >= file_size:
        return None
    return start, end


def _iter_file(path: Path, start: int, end: int):
    """Yield bytes of ``path`` from ``start`` to ``end`` inclusive."""
    remaining = end - start + 1
    with open(path, "rb") as fh:
        fh.seek(start)
        while remaining > 0:
            chunk = fh.read(min(MAX_CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def range_file_response(
    path: Path,
    media_type: str = "video/mp4",
    filename: Optional[str] = None,
    request: Optional[Request] = None,
):
    """Serve ``path`` with HTTP range support.

    ``request`` is optional so existing call sites keep working; when omitted,
    range support is still advertised and the whole file is returned.
    """
    path = Path(path)
    if not path.exists():
        # Let the caller's 404 handling win by deferring to FileResponse.
        return FileResponse(str(path), media_type=media_type)

    file_size = path.stat().st_size
    headers = {
        "Accept-Ranges": "bytes",
        # The file can be rewritten by a subsequent analysis run; never cache it
        # as if it were immutable, or a player may hold a stale, shorter version.
        "Cache-Control": "no-store, max-age=0",
    }
    if filename:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    range_header = request.headers.get("range") if request is not None else None
    parsed = _parse_range(range_header, file_size) if range_header else None

    if parsed is None:
        if range_header:
            # Requested range cannot be satisfied for the bytes that exist yet
            # (common while the file is still growing). Tell the player so it
            # retries instead of giving up.
            return Response(
                status_code=416,
                headers={
                    **headers,
                    "Content-Range": f"bytes */{file_size}",
                },
            )
        return StreamingResponse(
            _iter_file(path, 0, file_size - 1),
            media_type=media_type,
            headers=headers,
        )

    start, end = parsed
    length = end - start + 1
    return StreamingResponse(
        _iter_file(path, start, end),
        status_code=206,
        media_type=media_type,
        headers={
            **headers,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
        },
    )
