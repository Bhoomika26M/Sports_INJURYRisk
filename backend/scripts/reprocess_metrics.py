"""Re-derive biomechanical metrics + analysis for existing videos from stored pose frames.

    python scripts/reprocess_metrics.py --dry-run          # list what would change
    python scripts/reprocess_metrics.py                    # all completed videos
    python scripts/reprocess_metrics.py --video <uuid>     # one video

Run once after deploying the engine upgrade (migration 0003). No pose model is re-run. Risk scores
from the previous engine are recomputed automatically the next time they are requested.
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import async_session_factory  # noqa: E402
from app.modules.pose.reprocess import reprocess_all  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", help="only this video id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    async with async_session_factory() as db:
        results = await reprocess_all(db, args.video, args.dry_run)
    for r in results:
        print(json.dumps(r))
    done = sum(r["status"] == "reprocessed" for r in results)
    print(f"{len(results)} video(s) seen, {done} reprocessed, {sum(r['status'] == 'error' for r in results)} error(s)")


if __name__ == "__main__":
    asyncio.run(main())
