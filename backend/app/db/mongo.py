"""Optional MongoDB access for document-style data (pose keypoints, video metadata).

When MONGO_URL is empty the application falls back to JSON files (see
services/pose_store.py), so MongoDB is not required for local development.
"""

from functools import lru_cache

from app.core.config import settings


@lru_cache
def get_mongo_db():
    if not settings.MONGO_URL:
        return None
    from pymongo import MongoClient

    client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=3000)
    return client[settings.MONGO_DB]
