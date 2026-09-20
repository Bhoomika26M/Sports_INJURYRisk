#!/usr/bin/env python3
"""
Dataset validation script for Sports Injury Risk Detection System.

This script:
- Inspects registered datasets
- Checks expected files
- Validates sample annotations
- Reports missing datasets
- Reports valid datasets
"""

import json
import os
import sys
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATASET_REGISTRY_PATH = PROJECT_ROOT / "datasets" / "registry" / "datasets.json"
SAMPLE_DATASET_PATH = PROJECT_ROOT / "datasets" / "sample" / "sample_pose.json"


def load_dataset_registry():
    """Load the dataset registry from JSON file."""
    try:
        with open(DATASET_REGISTRY_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Dataset registry not found at {DATASET_REGISTRY_PATH}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing dataset registry: {e}")
        return None


def validate_sample_dataset():
    """Validate the sample pose dataset."""
    print("\n" + "="*60)
    print("Validating Sample Pose Dataset")
    print("="*60)
    
    if not SAMPLE_DATASET_PATH.exists():
        print(f"[ERROR] Sample dataset file not found at {SAMPLE_DATASET_PATH}")
        return False
    
    try:
        with open(SAMPLE_DATASET_PATH, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing sample dataset: {e}")
        return False
    
    # Validate structure
    if "dataset_info" not in data:
        print("[ERROR] Missing 'dataset_info' field")
        return False
    
    if "annotations" not in data:
        print("[ERROR] Missing 'annotations' field")
        return False
    
    if not isinstance(data["annotations"], list):
        print("[ERROR] 'annotations' must be a list")
        return False
    
    print(f"[OK] Dataset info: {data['dataset_info'].get('name', 'Unknown')}")
    print(f"[OK] Version: {data['dataset_info'].get('version', 'Unknown')}")
    print(f"[OK] Number of annotations: {len(data['annotations'])}")
    
    # Validate each annotation
    expected_keypoints = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    
    for i, annotation in enumerate(data["annotations"]):
        print(f"\n--- Annotation {i + 1} ---")
        
        if "person_id" not in annotation:
            print(f"[ERROR] Missing 'person_id' in annotation {i + 1}")
            return False
        
        if "keypoints" not in annotation:
            print(f"[ERROR] Missing 'keypoints' in annotation {i + 1}")
            return False
        
        if not isinstance(annotation["keypoints"], list):
            print(f"[ERROR] 'keypoints' must be a list in annotation {i + 1}")
            return False
        
        print(f"[OK] Person ID: {annotation['person_id']}")
        print(f"[OK] Number of keypoints: {len(annotation['keypoints'])}")
        
        # Validate keypoints structure
        keypoint_names = [kp["name"] for kp in annotation["keypoints"]]
        missing_keypoints = set(expected_keypoints) - set(keypoint_names)
        
        if missing_keypoints:
            print(f"[WARN] Missing keypoints: {missing_keypoints}")
        
        # Validate keypoint format
        for kp in annotation["keypoints"]:
            if not all(key in kp for key in ["name", "x", "y", "confidence"]):
                print(f"[ERROR] Invalid keypoint format: {kp}")
                return False
            
            if not isinstance(kp["x"], (int, float)) or not isinstance(kp["y"], (int, float)):
                print(f"[ERROR] Invalid coordinates in keypoint: {kp}")
                return False
            
            if not isinstance(kp["confidence"], (int, float)) or not (0 <= kp["confidence"] <= 1):
                print(f"[ERROR] Invalid confidence in keypoint: {kp}")
                return False
        
        print(f"[OK] All keypoints have valid format")
    
    print("\n[OK] Sample dataset validation PASSED")
    return True


def check_dataset_files(dataset):
    """Check if dataset files exist based on local_path."""
    if not dataset.get("local_path"):
        return False
    
    local_path = Path(dataset["local_path"])
    if not local_path.exists():
        return False
    
    return True


def generate_report(datasets):
    """Generate a comprehensive report on dataset status."""
    print("\n" + "="*60)
    print("DATASET INTEGRATION REPORT")
    print("="*60)
    
    status_counts = {
        "sample_integrated": 0,
        "not_downloaded": 0,
        "available": 0,
        "requires_manual_download": 0
    }
    
    print("\nRegistered Datasets:")
    print("-" * 60)
    
    for dataset in datasets:
        status = dataset.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        status_symbol = "[OK]" if status == "sample_integrated" else "[WARN]"
        print(f"\n{status_symbol} {dataset['name']}")
        print(f"   Purpose: {dataset['purpose']}")
        print(f"   Modality: {dataset['modality']}")
        print(f"   Status: {status}")
        print(f"   Source: {dataset['source']}")
        
        if dataset.get("local_path"):
            file_exists = check_dataset_files(dataset)
            status = "[OK] exists" if file_exists else "[ERROR] missing"
            print(f"   Local Path: {dataset['local_path']} ({status})")
        else:
            print(f"   Local Path: Not set")
        
        print(f"   License: {dataset.get('license_notes', 'N/A')}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total datasets registered: {len(datasets)}")
    print(f"Sample integrated: {status_counts['sample_integrated']}")
    print(f"Not downloaded: {status_counts['not_downloaded']}")
    print(f"Available: {status_counts['available']}")
    print(f"Requires manual download: {status_counts['requires_manual_download']}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if status_counts['not_downloaded'] > 0:
        print("[WARN] Some datasets are not downloaded.")
        print("   Refer to datasets/README.md for download instructions.")
    
    if status_counts['sample_integrated'] > 0:
        print("[OK] Sample dataset is integrated and validated.")
        print("   The system is ready for Milestone 2 pose estimation development.")
    
    print("\n" + "="*60)


def main():
    """Main validation function."""
    print("Sports Injury Risk Detection - Dataset Validation")
    print("="*60)
    
    # Load dataset registry
    datasets = load_dataset_registry()
    if not datasets:
        print("❌ Failed to load dataset registry")
        return 1
    
    print(f"[OK] Loaded {len(datasets)} registered datasets")
    
    # Validate sample dataset
    sample_valid = validate_sample_dataset()
    
    # Generate report
    generate_report(datasets)
    
    # Final status
    print("\n" + "="*60)
    if sample_valid:
        print("[OK] VALIDATION COMPLETE - Sample dataset is valid")
        return 0
    else:
        print("[ERROR] VALIDATION FAILED - Sample dataset has errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
