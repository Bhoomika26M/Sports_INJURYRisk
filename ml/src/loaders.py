import os
import cv2
import json
import numpy as np

class COCOLoader:
    def __init__(self, ann_file, img_dir):
        """
        Initialize the COCO keypoints loader.
        Use pycocotools if available, else fallback to standard JSON reading.
        """
        self.img_dir = img_dir
        
        try:
            from pycocotools.coco import COCO
            self.coco = COCO(ann_file)
            self.img_ids = self.coco.getImgIds(catIds=self.coco.getCatIds(catNms=['person']))
            self.use_pycocotools = True
        except ImportError:
            self.use_pycocotools = False
            with open(ann_file, 'r') as f:
                data = json.load(f)
            self.images = {img['id']: img for img in data['images']}
            self.annotations = [ann for ann in data['annotations'] if ann.get('keypoints') is not None and ann.get('num_keypoints', 0) > 0]
            self.img_ids = list(set([ann['image_id'] for ann in self.annotations]))
            # Group annotations by image_id
            self.img_to_anns = {img_id: [] for img_id in self.img_ids}
            for ann in self.annotations:
                self.img_to_anns[ann['image_id']].append(ann)

    def get_sample(self, idx):
        if idx >= len(self.img_ids):
            raise IndexError("Index out of bounds")

        img_id = self.img_ids[idx]
        
        if self.use_pycocotools:
            img_info = self.coco.loadImgs(img_id)[0]
            ann_ids = self.coco.getAnnIds(imgIds=img_id, iscrowd=False)
            anns = self.coco.loadAnns(ann_ids)
        else:
            img_info = self.images[img_id]
            anns = self.img_to_anns[img_id]

        img_path = os.path.join(self.img_dir, img_info['file_name'])
        
        # We might not have the image downloaded locally, so handle missing
        if os.path.exists(img_path):
            img = cv2.imread(img_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            # Return a dummy image if not found for testing logic
            img = np.zeros((img_info['height'], img_info['width'], 3), dtype=np.uint8)

        # Get keypoints for the first person in the image
        keypoints = []
        for ann in anns:
            if 'keypoints' in ann and ann['num_keypoints'] > 0:
                kpts = np.array(ann['keypoints']).reshape(-1, 3)
                keypoints.append(kpts)
        
        return img, keypoints


class MPIILoader:
    def __init__(self, ann_file, img_dir):
        """
        Initialize MPII loader.
        Expects annotations converted to a JSON format for simplicity.
        """
        self.img_dir = img_dir
        with open(ann_file, 'r') as f:
            self.data = json.load(f)

    def get_sample(self, idx):
        if idx >= len(self.data):
            raise IndexError("Index out of bounds")

        sample = self.data[idx]
        img_name = sample['image']
        img_path = os.path.join(self.img_dir, img_name)

        if os.path.exists(img_path):
            img = cv2.imread(img_path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img = np.zeros((256, 256, 3), dtype=np.uint8)
        else:
            img = np.zeros((256, 256, 3), dtype=np.uint8)

        # Standardize keypoints array
        keypoints = np.array(sample.get('joints', [])).reshape(-1, 2)
        # Add visibility flag for consistency with COCO (x, y, v)
        vis = np.array(sample.get('joint_vis', [1]*len(keypoints))).reshape(-1, 1)
        keypoints_with_vis = np.hstack([keypoints, vis]) if len(keypoints) > 0 else np.array([])
        
        return img, [keypoints_with_vis]
