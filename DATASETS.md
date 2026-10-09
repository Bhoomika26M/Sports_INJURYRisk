# Sports Biomechanics Datasets Collection

As part of Milestone 1, here are the recommended datasets collected and linked for further training and evaluation of the Pose Estimation and Injury Prediction Engine.

## 1. Human3.6M Dataset
- **Purpose**: Human pose estimation, joint tracking, movement analysis.
- **Access**: [Human3.6M Official Site](http://vision.imar.ro/human3.6m/description.php)
- **Description**: Contains 3.6 million 3D human poses and corresponding images, ideal for training robust 3D keypoint detection models.

## 2. MPII Human Pose Dataset
- **Purpose**: Body keypoint detection, activity recognition.
- **Access**: [MPII Dataset](http://human-pose.mpi-inf.mpg.de/)
- **Description**: Includes around 25K images containing over 40K people with annotated body joints, covering a wide range of human activities.

## 3. COCO Keypoints Dataset
- **Purpose**: Pose estimation training, human motion analysis.
- **Access**: [COCO Keypoints Task](https://cocodataset.org/#keypoints-2018)
- **Description**: Contains over 200,000 images and 250,000 person instances labeled with keypoints, standard for 2D pose estimation models.

## 4. SportsPose Dataset
- **Purpose**: Sports-specific movement analysis, athlete posture assessment.
- **Access**: [SportsPose Documentation / Repo] (Search via academic channels / papers)
- **Description**: Highly specialized for high-speed, multi-angle sports activities, providing accurate tracking under occlusion and motion blur.

## 5. FIFA Injury Dataset (Reference)
- **Purpose**: Injury trend analysis, risk factor modeling.
- **Access**: [FIFA Medical Research](https://www.fifa.com/medical/research)
- **Description**: Contains real-world injury statistics to help tune the risk scoring model to real injury incidence rates in specific sports like football/soccer.

---
**Note**: The engine currently utilizes an off-the-shelf implementation (MediaPipe) that was trained on datasets similar to COCO/MPII, but for custom model fine-tuning, you should download and mount these datasets locally.
