import json
import os
from pathlib import Path
from typing import List, Dict, Any
from app.schemas.dataset import DatasetResponse

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATASET_REGISTRY_PATH = PROJECT_ROOT / "datasets" / "registry" / "datasets.json"


def load_dataset_registry() -> List[Dict[str, Any]]:
    """Load the dataset registry from JSON file."""
    try:
        with open(str(DATASET_REGISTRY_PATH), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def get_registered_datasets() -> List[DatasetResponse]:
    """Get all registered datasets with their status."""
    datasets = load_dataset_registry()
    return [DatasetResponse(**dataset) for dataset in datasets]


def get_dataset_by_name(name: str) -> Dict[str, Any]:
    """Get a specific dataset by name."""
    datasets = load_dataset_registry()
    for dataset in datasets:
        if dataset["name"] == name:
            return dataset
    return None
