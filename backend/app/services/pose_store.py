"""Persist per-video pose payloads: MongoDB when configured, JSON files otherwise."""

import json
from pathlib import Path

from app.core.config import settings
from app.db.mongo import get_mongo_db


def _file_path(video_id: int) -> Path:
    return Path(settings.POSE_DIR) / f"{int(video_id)}.json"


def save_pose(video_id: int, payload: dict) -> None:
    mongo = get_mongo_db()
    if mongo is not None:
        mongo.pose.replace_one({"_id": video_id}, {"_id": video_id, **payload}, upsert=True)
        return
    path = _file_path(video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def load_pose(video_id: int) -> dict | None:
    mongo = get_mongo_db()
    if mongo is not None:
        doc = mongo.pose.find_one({"_id": video_id})
        if doc:
            doc.pop("_id", None)
        return doc
    path = _file_path(video_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())
