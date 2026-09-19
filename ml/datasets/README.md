# Datasets

This directory contains placeholder documentation and loaders for the datasets used in the sports injury risk detection project.

## 1. COCO (Common Objects in Context) Keypoints
- **Source**: [https://cocodataset.org/#keypoints-2017](https://cocodataset.org/#keypoints-2017)
- **License**: Creative Commons Attribution 4.0 License (images)
- **Size**: ~18 GB (2017 Train images) + ~1 GB (Train/Val annotations)
- **Download Steps**:
  1. Download the 2017 Train images: `wget http://images.cocodataset.org/zips/train2017.zip`
  2. Download the 2017 Val images: `wget http://images.cocodataset.org/zips/val2017.zip`
  3. Download the 2017 Train/Val annotations: `wget http://images.cocodataset.org/annotations/annotations_trainval2017.zip`
  4. Extract all zip files into `ml/datasets/coco/`.

## 2. MPII Human Pose Dataset
- **Source**: [http://human-pose.mpi-inf.mpg.de/](http://human-pose.mpi-inf.mpg.de/)
- **License**: Non-commercial use for research purposes
- **Size**: ~12 GB (images) + ~50 MB (annotations)
- **Download Steps**:
  1. Download the images: `wget https://datasets.d2.mpi-inf.mpg.de/andriluka14cvpr/mpii_human_pose_v1.tar.gz`
  2. Download the annotations: `wget https://datasets.d2.mpi-inf.mpg.de/andriluka14cvpr/mpii_human_pose_v1_u12_2.zip`
  3. Extract all files into `ml/datasets/mpii/`.
