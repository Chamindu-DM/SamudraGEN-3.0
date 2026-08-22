#!/usr/bin/env python3
"""
Benchmark Ground-Truth Evaluator (t=120s to t=133s)
Evaluates HomographyLCDTracker + MultimeterDigitCNN against the 14 human-verified ground-truth readings.
"""

import cv2
import numpy as np
import os
import json
import torch
import torch.nn as nn

import sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
MODEL_PATH = os.path.join(BASE_DIR, "digit_cnn.pt")

from multimeter_extractor.src.homography_tracker import HomographyLCDTracker

# User's human-eye verified ground truth
GROUND_TRUTH = {
    120: 1.571,
    121: 1.358,
    122: 1.212,
    123: 1.099,
    124: 1.007,
    125: 0.929,
    126: 0.863,
    127: 0.805,
    128: 0.756,
    129: 1.742,
    130: 2.86,
    131: 5.05,
    132: 4.19,
    133: 2.62
}

SLOT_BOUNDS = [
    (0.14, 0.33),  # Slot 0
    (0.36, 0.55),  # Slot 1
    (0.58, 0.77),  # Slot 2
    (0.79, 0.98),  # Slot 3
]
DIGIT_Y = (0.24, 0.94)

class MultimeterDigitCNN(nn.Module):
    def __init__(self):
        super(MultimeterDigitCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(128 * 8 * 6, 128),
            nn.ReLU(),
            nn.Linear(128, 11)
        )

    def forward(self, x):
        feat = self.features(x)
        feat = feat.view(feat.size(0), -1)
        out = self.classifier(feat)
        return out


def decode_lcd_reading(model, lcd_img):
    h, w = lcd_img.shape[:2]
    gray = cv2.cvtColor(lcd_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    digits = []
    
    for s_idx, (x1_f, x2_f) in enumerate(SLOT_BOUNDS):
        sx1, sx2 = int(x1_f * w), int(x2_f * w)
        sy1, sy2 = int(DIGIT_Y[0] * h), int(DIGIT_Y[1] * h)
        patch = enhanced[sy1:sy2, sx1:sx2]
        patch_resized = cv2.resize(patch, (48, 64))
        
        norm = (patch_resized.astype(np.float32) / 255.0 - 0.5) / 0.5
        t_img = torch.tensor(norm, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        
        with torch.no_grad():
            out = model(t_img)
            pred_class = torch.argmax(out, dim=1).item()
            
        if pred_class != 10:  # not blank
            digits.append((s_idx, str(pred_class)))

    if not digits:
        return None, ""
        
    num_str = "".join([d[1] for d in digits])
    
    # Decimal point placement rules for auto-ranging UT33A+
    if len(num_str) == 4:
        val_str = f"{num_str[0]}.{num_str[1:]}"
    elif len(num_str) == 3:
        val_str = f"{num_str[0]}.{num_str[1:]}"
    elif len(num_str) == 2:
        val_str = f"{num_str[0]}.{num_str[1:]}"
    else:
        val_str = num_str
        
    try:
        val = float(val_str)
        return val, val_str
    except Exception:
        return None, val_str


def main():
    model = MultimeterDigitCNN()
    model.load_state_dict(torch.load(MODEL_PATH))
    model.eval()
    
    tracker = HomographyLCDTracker()
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print("\n" + "="*60)
    print(" 🎯 BENCHMARK TEST ON USER HUMAN-EYE GROUND TRUTH (120s..133s) ")
    print("="*60)
    print(f"{'Time (s)':<10} | {'Human True Value':<18} | {'Model Predicted':<16} | {'Status':<6}")
    print("-" * 60)
    
    correct = 0
    total = len(GROUND_TRUTH)
    
    # We step from 116s sequentially to 133s so optical flow tracking has temporal history
    for t_sec in range(116, 134):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
        ret, frame = cap.read()
        if not ret:
            continue
            
        corners = tracker.track_lcd_corners(frame, t_sec)
        warped_lcd = tracker.warp_lcd_screen(frame, corners)
        
        if t_sec in GROUND_TRUTH:
            true_val = GROUND_TRUTH[t_sec]
            pred_val, raw_txt = decode_lcd_reading(model, warped_lcd)
            
            is_match = (pred_val is not None and abs(pred_val - true_val) < 1e-3)
            if is_match:
                correct += 1
                status = "✅ MATCH"
            else:
                status = f"❌ MISMATCH (got {pred_val})"
                
            print(f"{t_sec:<10} | {true_val:<18} | {str(pred_val):<16} | {status}")
            
    cap.release()
    print("-" * 60)
    print(f"Benchmark Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")


if __name__ == "__main__":
    main()
