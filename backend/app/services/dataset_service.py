"""
Dataset Service for managing dataset specifications, adapters,
sample generation, and FIFA clinical benchmark evaluations.
"""

from typing import Dict, Any, List, Optional
from app.core.dataset_registry import DATASET_REGISTRY
from app.utils.dataset_adapters import (
    convert_coco_keypoints,
    convert_mpii_joints,
    convert_human36m_joints,
    convert_sportspose_frame,
    generate_sample_dataset_payload,
    evaluate_fifa_risk_compliance
)
from app.utils.biomechanics import process_frame_biomechanics

class DatasetService:
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all integrated datasets with metadata."""
        return list(DATASET_REGISTRY.values())

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific dataset."""
        return DATASET_REGISTRY.get(dataset_id.lower())

    def get_fifa_risk_factors(self) -> Dict[str, Any]:
        """Retrieve clinical FIFA 11+ risk factors and thresholds."""
        return DATASET_REGISTRY["fifa_reference"]

    def get_dataset_sample(self, dataset_id: str) -> Dict[str, Any]:
        """Generate a realistic sample payload for benchmarking/testing."""
        return generate_sample_dataset_payload(dataset_id.lower())

    def convert_and_analyze(self, dataset_id: str, payload: Dict[str, Any], width: int = 640, height: int = 480) -> Dict[str, Any]:
        """
        Converts external dataset keypoints into platform landmarks,
        computes biomechanical metrics, and evaluates FIFA clinical compliance.
        """
        ds_id = dataset_id.lower()
        if ds_id not in DATASET_REGISTRY:
            raise ValueError(f"Unsupported dataset: {dataset_id}")

        timestamp_ms = payload.get("timestamp_ms", 0.0)

        # 1. Convert to standard landmarks
        if ds_id == "coco":
            kpts = payload.get("keypoints", [])
            landmarks = convert_coco_keypoints(kpts, width=width, height=height)
        elif ds_id == "mpii":
            joints = payload.get("joints", [])
            landmarks = convert_mpii_joints(joints, width=width, height=height)
        elif ds_id == "human36m":
            joints_3d = payload.get("joints_3d_mm", payload.get("joints", []))
            landmarks = convert_human36m_joints(joints_3d)
        elif ds_id == "sportspose":
            landmarks = convert_sportspose_frame(payload)
        elif ds_id == "fifa_reference":
            # For FIFA reference, evaluate direct metrics passed in payload
            metrics = payload.get("metrics", {})
            return {
                "dataset_id": ds_id,
                "input_type": "clinical_metrics",
                "fifa_evaluation": evaluate_fifa_risk_compliance(metrics)
            }
        else:
            raise ValueError(f"No adapter available for {dataset_id}")

        frame_data = {
            "timestamp_ms": timestamp_ms,
            "landmarks": landmarks
        }

        # 2. Compute biomechanics from landmarks
        biomechanics = process_frame_biomechanics(frame_data, width, height)

        # 3. Evaluate against FIFA 11+ clinical guidelines
        fifa_evaluation = evaluate_fifa_risk_compliance(biomechanics)

        return {
            "dataset_id": ds_id,
            "dataset_name": DATASET_REGISTRY[ds_id]["name"],
            "converted_landmarks_count": len(landmarks),
            "landmarks": landmarks,
            "biomechanics": biomechanics,
            "fifa_evaluation": fifa_evaluation
        }

dataset_service = DatasetService()
