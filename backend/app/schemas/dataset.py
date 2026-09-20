from pydantic import BaseModel
from typing import Optional


class DatasetResponse(BaseModel):
    name: str
    source: str
    purpose: str
    modality: str
    annotation_format: str
    expected_keypoints: Optional[str]
    status: str
    local_path: Optional[str]
    license_notes: Optional[str]
    preprocessing_status: Optional[str]
