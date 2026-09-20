from fastapi import APIRouter, Depends
from typing import List
from app.schemas.dataset import DatasetResponse
from app.services.dataset_service import get_registered_datasets
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("/", response_model=List[DatasetResponse])
def get_datasets(current_user: User = Depends(get_current_active_user)):
    """
    Get all registered datasets and their integration status.
    
    Available to all authenticated users.
    
    Returns information about:
    - Human3.6M
    - MPII Human Pose
    - COCO Keypoints
    - SportsPose
    - FIFA Injury Dataset
    
    Each dataset includes:
    - name
    - source
    - purpose
    - modality
    - annotation_format
    - expected_keypoints
    - status (available, not_downloaded, sample_integrated, requires_manual_download)
    - local_path
    - license_notes
    - preprocessing_status
    """
    return get_registered_datasets()
