from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from app.services.dataset_service import dataset_service

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
def get_datasets() -> Any:
    """
    List all integrated benchmark and clinical datasets:
    - Human3.6M (3D pose estimation & tracking)
    - MPII Human Pose (2D keypoints & activity recognition)
    - COCO Keypoints (pose estimation backbone standard)
    - SportsPose (sports-specific athletic movements)
    - FIFA Injury Reference (FIFA 11+ clinical injury risk factors)
    """
    return dataset_service.list_datasets()

@router.get("/fifa/risk-factors", response_model=Dict[str, Any])
def get_fifa_risk_factors() -> Any:
    """
    Retrieve clinical injury prevention thresholds, injury mechanisms (ACL, hamstring, patellar),
    and FIFA 11+ intervention protocols.
    """
    return dataset_service.get_fifa_risk_factors()

@router.get("/{dataset_id}", response_model=Dict[str, Any])
def get_dataset(dataset_id: str) -> Any:
    """
    Get full specifications, keypoint topology, and clinical role for a specific dataset.
    """
    data = dataset_service.get_dataset(dataset_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return data

@router.get("/{dataset_id}/sample", response_model=Dict[str, Any])
def get_dataset_sample(dataset_id: str) -> Any:
    """
    Generate a realistic sample frame in the dataset's native schema for testing and validation.
    """
    try:
        return dataset_service.get_dataset_sample(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/convert", response_model=Dict[str, Any])
def convert_and_analyze_dataset(
    dataset_id: str = Query(..., description="Target dataset format: coco, mpii, human36m, sportspose, or fifa_reference"),
    payload: Dict[str, Any] = Body(..., description="Raw frame payload matching dataset format"),
    width: int = Query(640, description="Image/frame width for coordinate normalization"),
    height: int = Query(480, description="Image/frame height for coordinate normalization")
) -> Any:
    """
    Convert an external pose dataset frame (COCO, MPII, Human3.6M, or SportsPose) into
    standardized platform landmarks, calculate biomechanics, and benchmark against FIFA clinical rules.
    """
    try:
        return dataset_service.convert_and_analyze(
            dataset_id=dataset_id,
            payload=payload,
            width=width,
            height=height
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset processing error: {str(e)}")
