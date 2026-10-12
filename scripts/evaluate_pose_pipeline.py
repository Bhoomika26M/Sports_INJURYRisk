"""
Pose Pipeline Evaluation Script

Evaluates the BlazePose pose estimation pipeline against dataset annotations.

Supported metrics:
- PCK (Percentage of Correct Keypoints)
- PCKh (PCK normalized by head size)
- PCK@0.1, PCK@0.2 (PCK with different thresholds)
- Keypoint localization error
- Valid landmark percentage
- Confidence metrics
- Processing latency

Usage:
    python scripts/evaluate_pose_pipeline.py --dataset coco --data-dir /path/to/coco
    python scripts/evaluate_pose_pipeline.py --dataset mpii --data-dir /path/to/mpii
"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import cv2

from app.datasets import get_adapter
from app.pose.mediapipe_pose import MediaPipeBlazePoseEstimator
from app.pose.estimator import Keypoint


class PosePipelineEvaluator:
    """
    Evaluator for the pose estimation pipeline.
    
    Evaluates BlazePose against ground truth annotations.
    """
    
    def __init__(self, dataset_name: str, data_dir: str):
        """
        Initialize evaluator.
        
        Args:
            dataset_name: Name of dataset (coco, mpii, human36m, sportspose)
            data_dir: Path to dataset directory
        """
        self.dataset_name = dataset_name
        self.data_dir = Path(data_dir)
        
        # Load dataset adapter
        self.adapter = get_adapter(dataset_name, str(self.data_dir))
        
        # Initialize BlazePose estimator
        self.pose_estimator = MediaPipeBlazePoseEstimator()
        
        # Evaluation results
        self.results = {
            "dataset": dataset_name,
            "data_dir": str(self.data_dir),
            "metrics": {},
            "errors": []
        }
    
    def evaluate(self, num_samples: int = 100) -> Dict:
        """
        Run evaluation on dataset samples.
        
        Args:
            num_samples: Number of samples to evaluate
        
        Returns:
            Dictionary with evaluation results
        """
        print(f"Evaluating pose pipeline on {self.dataset_name} dataset...")
        print(f"Data directory: {self.data_dir}")
        
        try:
            # Load annotations
            print("Loading annotations...")
            annotations = self.adapter.load_annotations()
            
            if not annotations:
                print("WARNING: No annotations loaded. Dataset may not be downloaded.")
                self.results["status"] = "no_data"
                self.results["message"] = "Dataset not downloaded or empty"
                return self.results
            
            print(f"Loaded {len(annotations)} annotations")
            
            # Limit samples
            annotations = annotations[:num_samples]
            print(f"Evaluating {len(annotations)} samples")
            
            # Run evaluation
            self._run_evaluation(annotations)
            
            self.results["status"] = "success"
            
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            self.results["status"] = "dataset_not_found"
            self.results["message"] = str(e)
            self.results["errors"].append(str(e))
            
        except Exception as e:
            print(f"ERROR: {e}")
            self.results["status"] = "error"
            self.results["message"] = str(e)
            self.results["errors"].append(str(e))
        
        return self.results
    
    def _run_evaluation(self, annotations: List[Dict]):
        """Run evaluation on annotations."""
        pck_scores = []
        pckh_scores = []
        localization_errors = []
        valid_landmark_percentages = []
        confidence_scores = []
        processing_times = []
        
        for i, annotation in enumerate(annotations):
            print(f"Processing sample {i+1}/{len(annotations)}...")
            
            try:
                # Get image path from annotation
                image_path = self._get_image_path(annotation)
                
                if not image_path or not Path(image_path).exists():
                    print(f"  WARNING: Image not found: {image_path}")
                    continue
                
                # Load image
                image = cv2.imread(str(image_path))
                if image is None:
                    print(f"  WARNING: Failed to load image: {image_path}")
                    continue
                
                # Get ground truth keypoints
                gt_keypoints = self._get_ground_truth_keypoints(annotation)
                
                if not gt_keypoints:
                    print(f"  WARNING: No ground truth keypoints")
                    continue
                
                # Run pose estimation
                start_time = time.time()
                predicted_keypoints = self.pose_estimator.estimate(image)
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                # Map ground truth to BlazePose format
                gt_blazepose = self.adapter.map_keypoints_to_blazepose(gt_keypoints)
                
                # Calculate metrics
                metrics = self._calculate_metrics(
                    predicted_keypoints,
                    gt_blazepose,
                    image.shape
                )
                
                pck_scores.append(metrics.get("pck"))
                pckh_scores.append(metrics.get("pckh"))
                localization_errors.append(metrics.get("localization_error"))
                valid_landmark_percentages.append(metrics.get("valid_landmark_percentage"))
                confidence_scores.append(metrics.get("mean_confidence"))
                
            except Exception as e:
                print(f"  ERROR processing sample: {e}")
                self.results["errors"].append(f"Sample {i}: {str(e)}")
        
        # Calculate aggregate metrics
        self.results["metrics"] = {
            "num_samples": len(annotations),
            "num_processed": len(pck_scores),
            "pck": float(np.mean(pck_scores)) if pck_scores else None,
            "pck_std": float(np.std(pck_scores)) if pck_scores else None,
            "pckh": float(np.mean(pckh_scores)) if pckh_scores else None,
            "pckh_std": float(np.std(pckh_scores)) if pckh_scores else None,
            "mean_localization_error": float(np.mean(localization_errors)) if localization_errors else None,
            "valid_landmark_percentage": float(np.mean(valid_landmark_percentages)) if valid_landmark_percentages else None,
            "mean_confidence": float(np.mean(confidence_scores)) if confidence_scores else None,
            "mean_processing_time": float(np.mean(processing_times)) if processing_times else None,
            "fps": 1.0 / np.mean(processing_times) if processing_times and np.mean(processing_times) > 0 else None
        }
        
        print("\n=== Evaluation Results ===")
        print(f"Samples processed: {self.results['metrics']['num_processed']}/{self.results['metrics']['num_samples']}")
        print(f"PCK: {self.results['metrics']['pck']:.3f} ± {self.results['metrics']['pck_std']:.3f}")
        print(f"PCKh: {self.results['metrics']['pckh']:.3f} ± {self.results['metrics']['pckh_std']:.3f}")
        print(f"Mean localization error: {self.results['metrics']['mean_localization_error']:.2f} pixels")
        print(f"Valid landmark percentage: {self.results['metrics']['valid_landmark_percentage']:.1f}%")
        print(f"Mean confidence: {self.results['metrics']['mean_confidence']:.3f}")
        print(f"Mean processing time: {self.results['metrics']['mean_processing_time']:.3f}s")
        print(f"FPS: {self.results['metrics']['fps']:.1f}")
    
    def _get_image_path(self, annotation: Dict) -> str:
        """Get image path from annotation."""
        # This is dataset-specific
        # Placeholder implementation
        return None
    
    def _get_ground_truth_keypoints(self, annotation: Dict) -> List[Tuple[float, float]]:
        """Get ground truth keypoints from annotation."""
        # This is dataset-specific
        # Placeholder implementation
        return []
    
    def _calculate_metrics(
        self,
        predicted: List[Keypoint],
        ground_truth: List[Keypoint],
        image_shape: Tuple[int, int, int]
    ) -> Dict:
        """
        Calculate evaluation metrics.
        
        Args:
            predicted: Predicted keypoints
            ground_truth: Ground truth keypoints
            image_shape: Image shape (height, width, channels)
        
        Returns:
            Dictionary with metrics
        """
        # Create dictionaries for quick lookup
        pred_dict = {kp.name: kp for kp in predicted}
        gt_dict = {kp.name: kp for kp in ground_truth}
        
        # Calculate distances for each keypoint
        distances = []
        valid_count = 0
        total_count = 0
        confidences = []
        
        for name, gt_kp in gt_dict.items():
            total_count += 1
            
            if name not in pred_dict:
                continue
            
            pred_kp = pred_dict[name]
            
            # Calculate Euclidean distance
            distance = np.sqrt(
                (pred_kp.x - gt_kp.x)**2 + (pred_kp.y - gt_kp.y)**2
            )
            distances.append(distance)
            
            if pred_kp.confidence > 0.3:
                valid_count += 1
            
            confidences.append(pred_kp.confidence)
        
        # Calculate PCK (threshold = 0.1 * image diagonal)
        if distances:
            image_diagonal = np.sqrt(image_shape[0]**2 + image_shape[1]**2)
            threshold = 0.1 * image_diagonal
            correct = sum(1 for d in distances if d < threshold)
            pck = correct / len(distances) if distances else 0.0
        else:
            pck = 0.0
        
        # Calculate PCKh (threshold = 0.5 * head size)
        # Simplified: use 0.1 * image height as head size proxy
        head_size = 0.1 * image_shape[0]
        if distances:
            threshold_h = 0.5 * head_size
            correct_h = sum(1 for d in distances if d < threshold_h)
            pckh = correct_h / len(distances) if distances else 0.0
        else:
            pckh = 0.0
        
        return {
            "pck": pck,
            "pckh": pckh,
            "localization_error": np.mean(distances) if distances else 0.0,
            "valid_landmark_percentage": (valid_count / total_count * 100) if total_count > 0 else 0.0,
            "mean_confidence": np.mean(confidences) if confidences else 0.0
        }
    
    def save_results(self, output_path: str):
        """Save evaluation results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate pose pipeline")
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=["coco", "mpii", "human36m", "sportspose"],
        help="Dataset name"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Path to dataset directory"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=100,
        help="Number of samples to evaluate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.json",
        help="Output JSON file"
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    evaluator = PosePipelineEvaluator(args.dataset, args.data_dir)
    results = evaluator.evaluate(num_samples=args.num_samples)
    
    # Save results
    evaluator.save_results(args.output)
    
    # Print status
    if results["status"] == "success":
        print("\n✓ Evaluation completed successfully")
    elif results["status"] == "dataset_not_found":
        print("\n✗ Dataset not found. Please download the dataset first.")
        print(f"  See docs/DATASETS.md for download instructions.")
    else:
        print(f"\n✗ Evaluation failed: {results.get('message', 'Unknown error')}")


if __name__ == "__main__":
    main()
