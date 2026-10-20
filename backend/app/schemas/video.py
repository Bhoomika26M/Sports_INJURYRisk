from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Activity = Literal[
    "running", "sprinting", "jumping", "squatting", "landing", "throwing", "cutting", "drill"
]


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    activity: str
    original_filename: str
    fps: float | None
    width: int | None
    height: int | None
    frame_count: int | None
    duration_s: float | None
    status: str
    error: str | None
    quality: dict
    created_at: datetime
