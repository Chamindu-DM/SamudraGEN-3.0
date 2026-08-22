#!/usr/bin/env python3
"""
Industrial YOLOv8 Digit & Decimal Detector Trainer
Generates character bounding-box dataset from 38 human-verified keyframes
with synthetic water spots, lighting, and blur augmentations, then fine-tunes YOLOv8n.
"""

import cv2
import numpy as np
import os
import json
import yaml
import shutil
from ultralytics import YOLO

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
LABELED_DIR = os.path.join(BASE_DIR, "labeled_data", "voltage")
YOLO_DATA_DIR = os.path.join(BASE_DIR, "yolo_dataset")
BASE_WEIGHTS = os.path.join(BASE_DIR, "yolov8n.pt")

# Classes: 0-9, dot (10), minus (11)
CLASSES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'dot', 'minus']
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}

# 4 Digit Slot X-bounds (normalized 0..1 in 400x180 crop)
SLOT_X_BOUNDS = [
    (0.15, 0.35),  # Slot 0
    (0.36, 0.56),  # Slot 1
    (0.57, 0.77),  # Slot 2
    (0.78, 0.98),  # Slot 3
]
DIGIT_Y_BOUND = (0.24, 0.94)


def create_boxes_for_labeled_crop(val_str):
    """
    Maps each digit and decimal point to its normalized bounding box (class_id, cx, cy, w, h).
    """
    has_minus = val_str.startswith('-')
    clean = val_str.lstrip('-')
    
    parts = clean.split('.')
    whole = parts[0]
    frac = parts[1] if len(parts) > 1 else ""
    digits_only = whole + frac
    total_digits = len(digits_only)
    
    if total_digits == 4:
        start_slot = 0
    elif total_digits == 3:
        start_slot = 1
    elif total_digits == 2:
        start_slot = 2
    else:
        start_slot = max(0, 4 - total_digits)
        
    boxes = []
    if has_minus:
        boxes.append((CLASS_TO_ID['minus'], 0.09, 0.58, 0.07, 0.08))
        
    dot_placed = False
    for i, ch in enumerate(digits_only):
        slot_idx = start_slot + i
        if slot_idx >= 4:
            break
            
        x1, x2 = SLOT_X_BOUNDS[slot_idx]
        y1, y2 = DIGIT_Y_BOUND
        
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        bw = (x2 - x1) * 0.90
        bh = (y2 - y1) * 0.95
        
        cid = CLASS_TO_ID[ch]
        boxes.append((cid, cx, cy, bw, bh))
        
        # Decimal point check
        if len(parts) > 1 and not dot_placed and (i + 1) == len(whole):
            dot_cx = x2 + 0.015
            dot_cy = 0.88
            dot_w = 0.04
            dot_h = 0.07
            boxes.append((CLASS_TO_ID['dot'], dot_cx, dot_cy, dot_w, dot_h))
            dot_placed = True
            
    return boxes


def augment_image(img):
    aug = img.copy()
    h, w = aug.shape[:2]
    
    # 1. Lighting and contrast shifts
    alpha = np.random.uniform(0.70, 1.35)
    beta = np.random.uniform(-35, 35)
    aug = np.clip(alpha * aug.astype(np.float32) + beta, 0, 255).astype(np.uint8)
    
    # 2. Synthetic water droplets / streaks
    num_spots = np.random.randint(1, 4)
    for _ in range(num_spots):
        sx = np.random.randint(int(w * 0.1), int(w * 0.9))
        sy = np.random.randint(int(h * 0.2), int(h * 0.9))
        sr = np.random.randint(5, 18)
        cv2.circle(aug, (sx, sy), sr, (240, 240, 240), -1)
        cv2.circle(aug, (sx, sy), sr, (160, 160, 160), 2)
        
    # 3. Slight blur
    if np.random.rand() > 0.4:
        k = np.random.choice([3, 5])
        aug = cv2.GaussianBlur(aug, (k, k), 0)
        
    return aug


def build_yolo_dataset():
    images_train = os.path.join(YOLO_DATA_DIR, "images", "train")
    labels_train = os.path.join(YOLO_DATA_DIR, "labels", "train")
    images_val = os.path.join(YOLO_DATA_DIR, "images", "val")
    labels_val = os.path.join(YOLO_DATA_DIR, "labels", "val")
    
    if os.path.exists(YOLO_DATA_DIR):
        shutil.rmtree(YOLO_DATA_DIR)
        
    for d in [images_train, labels_train, images_val, labels_val]:
        os.makedirs(d, exist_ok=True)
        
    with open(os.path.join(LABELED_DIR, "annotations.json")) as f:
        annotations = json.load(f)
        
    crops_dir = os.path.join(LABELED_DIR, "crops")
    items = list(annotations.items())
    
    # 30 training frames, 8 validation frames
    val_items = items[:8]
    train_items = items[8:]
    
    train_id = 0
    for k, item in train_items:
        val_str = item["value"]
        crop_path = os.path.join(crops_dir, item["crop_file"])
        img = cv2.imread(crop_path)
        if img is None:
            continue
            
        base_boxes = create_boxes_for_labeled_crop(val_str)
        
        # Save base image
        img_name = f"train_{train_id:04d}.jpg"
        cv2.imwrite(os.path.join(images_train, img_name), img)
        with open(os.path.join(labels_train, f"train_{train_id:04d}.txt"), "w") as lf:
            for b in base_boxes:
                lf.write(f"{b[0]} {b[1]:.4f} {b[2]:.4f} {b[3]:.4f} {b[4]:.4f}\n")
        train_id += 1
        
        # Save 25 augmented copies per base image
        for _ in range(25):
            aug_img = augment_image(img)
            img_name = f"train_{train_id:04d}.jpg"
            cv2.imwrite(os.path.join(images_train, img_name), aug_img)
            with open(os.path.join(labels_train, f"train_{train_id:04d}.txt"), "w") as lf:
                for b in base_boxes:
                    lf.write(f"{b[0]} {b[1]:.4f} {b[2]:.4f} {b[3]:.4f} {b[4]:.4f}\n")
            train_id += 1

    # Validation set
    val_id = 0
    for k, item in val_items:
        val_str = item["value"]
        crop_path = os.path.join(crops_dir, item["crop_file"])
        img = cv2.imread(crop_path)
        if img is None:
            continue
        base_boxes = create_boxes_for_labeled_crop(val_str)
        img_name = f"val_{val_id:04d}.jpg"
        cv2.imwrite(os.path.join(images_val, img_name), img)
        with open(os.path.join(labels_val, f"val_{val_id:04d}.txt"), "w") as lf:
            for b in base_boxes:
                lf.write(f"{b[0]} {b[1]:.4f} {b[2]:.4f} {b[3]:.4f} {b[4]:.4f}\n")
        val_id += 1

    data_yaml = {
        'path': os.path.abspath(YOLO_DATA_DIR),
        'train': 'images/train',
        'val': 'images/val',
        'names': {i: c for i, c in enumerate(CLASSES)}
    }
    yaml_path = os.path.join(YOLO_DATA_DIR, "data.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f)
        
    print(f"✅ Generated dataset: {train_id} training images, {val_id} validation images.")
    return yaml_path


def train_yolo(yaml_path):
    print("\n🚀 Training YOLOv8 Digit & Decimal Detector from pre-trained weights...")
    model = YOLO(BASE_WEIGHTS)
    
    project_dir = os.path.join(BASE_DIR, "yolo_runs")
    results = model.train(
        data=yaml_path,
        epochs=25,
        imgsz=384,
        batch=32,
        plots=True,
        device="mps",
        project=project_dir,
        name="digit_detector",
        exist_ok=True
    )
    
    best_pt = os.path.join(project_dir, "digit_detector", "weights", "best.pt")
    print(f"\n🎉 Training complete! Best YOLO model saved at: {best_pt}")
    return best_pt


def main():
    yaml_path = build_yolo_dataset()
    train_yolo(yaml_path)


if __name__ == "__main__":
    main()
