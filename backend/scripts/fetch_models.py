"""Download everything the video analysis needs, once, while you have internet: `python scripts/fetch_models.py`.

Without this the models are fetched on the first upload; on a venue's wifi (or offline) that upload fails.
Fetches: the YOLO person-tracker weights, the MediaPipe pose bundle, and an ffmpeg binary if the system has none
(used to validate uploads and to write the tracked video).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.pose import pipeline  # noqa: E402


def main() -> None:
    print("YOLO + MediaPipe models ...")
    pipeline.load_models()
    print("ffmpeg ...")
    exe = pipeline.ffmpeg_bin()
    print(f"ok: models in {os.path.abspath(pipeline._BACKEND_ROOT)}, ffmpeg = {exe or 'NOT AVAILABLE (uploads cannot be validated)'}")


if __name__ == "__main__":
    main()
