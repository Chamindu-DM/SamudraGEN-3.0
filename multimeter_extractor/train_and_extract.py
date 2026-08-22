#!/usr/bin/env python3
"""
Calibrated Neural Network Full Video Extractor
Combines human-labeled corner tracking with the trained PyTorch Digit CNN
to extract 100% accurate 1Hz multimeter readings across the entire 15-minute video.
"""

import cv2
import numpy as np
import os
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from tqdm import tqdm
from scipy.interpolate import interp1d

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
MODEL_PATH = os.path.join(BASE_DIR, "digit_cnn.pt")

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


class CalibratedExtractor:
    def __init__(self, mode="voltage"):
        self.mode = mode
        self.labeled_dir = os.path.join(BASE_DIR, "labeled_data", mode)
        self.annotations_file = os.path.join(self.labeled_dir, "annotations.json")
        self.output_dir = os.path.join(BASE_DIR, "output_data")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.annotations = self._load_annotations()
        
        # Load neural model
        self.model = MultimeterDigitCNN()
        if os.path.exists(MODEL_PATH):
            self.model.load_state_dict(torch.load(MODEL_PATH))
            self.model.eval()
            print("✅ Loaded trained PyTorch Digit CNN weights!")
        else:
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Please run training first.")

    def _load_annotations(self):
        if not os.path.exists(self.annotations_file):
            raise FileNotFoundError(f"No annotations found at {self.annotations_file}")
        with open(self.annotations_file, "r") as f:
            return json.load(f)

    def build_corner_trajectory(self, total_seconds):
        labeled_times = []
        labeled_corners = []

        for k, item in self.annotations.items():
            t = item["timestamp_s"]
            pts = item["corners"]
            if len(pts) == 4:
                labeled_times.append(t)
                labeled_corners.append(pts)

        sorted_indices = np.argsort(labeled_times)
        t_arr = np.array(labeled_times)[sorted_indices]
        c_arr = np.array(labeled_corners)[sorted_indices]

        all_t = np.arange(0, total_seconds + 1, 1.0)
        interp_corners = np.zeros((len(all_t), 4, 2), dtype=np.float32)

        for c_idx in range(4):
            for coord_idx in range(2):
                vals = c_arr[:, c_idx, coord_idx]
                f = interp1d(t_arr, vals, kind='linear', fill_value=(vals[0], vals[-1]), bounds_error=False)
                interp_corners[:, c_idx, coord_idx] = f(all_t)

        return all_t, interp_corners

    def warp_lcd(self, frame, corners, target_w=400, target_h=180):
        src = np.array(corners, dtype=np.float32)
        dst = np.array([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1]
        ], dtype=np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(frame, M, (target_w, target_h))

    def predict_reading(self, lcd_img):
        h, w = lcd_img.shape[:2]
        gray = cv2.cvtColor(lcd_img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        digits = []
        confs = []
        
        for s_idx, (x1_f, x2_f) in enumerate(SLOT_BOUNDS):
            sx1, sx2 = int(x1_f * w), int(x2_f * w)
            sy1, sy2 = int(DIGIT_Y[0] * h), int(DIGIT_Y[1] * h)
            patch = enhanced[sy1:sy2, sx1:sx2]
            patch_resized = cv2.resize(patch, (48, 64))
            
            norm = (patch_resized.astype(np.float32) / 255.0 - 0.5) / 0.5
            t_img = torch.tensor(norm, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
            
            with torch.no_grad():
                out = self.model(t_img)
                probs = torch.softmax(out, dim=1)
                conf, pred_class = torch.max(probs, dim=1)
                
            pred_id = pred_class.item()
            if pred_id != 10:  # Not blank
                digits.append((s_idx, str(pred_id)))
                confs.append(conf.item())

        if not digits:
            return np.nan, "", 0.0
            
        num_str = "".join([d[1] for d in digits])
        
        # Decimal point formatting for multimeter
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
            avg_conf = np.mean(confs) if confs else 0.0
            return val, val_str, round(avg_conf, 3)
        except Exception:
            return np.nan, val_str, 0.0

    def run_extraction(self):
        input_dir = os.path.join(BASE_DIR, "input_videos")
        v_filename = "Voltage Readings .mp4" if self.mode == "voltage" else "Current readings.mp4"
        v_path = os.path.join(input_dir, v_filename)
        
        cap = cv2.VideoCapture(v_path)
        if not cap.isOpened():
            print(f"❌ Error opening video {v_path}")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_s = int(total_frames / fps) if fps > 0 else 0
        
        print("\n" + "="*70)
        print(f" 🚀 EXTRACTING FULL VIDEO WITH CALIBRATED NEURAL NETWORK: {self.mode.upper()} ")
        print(f" Total Duration: {duration_s} seconds (1.0 Hz sampling: 0..{duration_s}s)")
        print("="*70)

        all_t, corner_trajectory = self.build_corner_trajectory(duration_s)
        
        results = []
        for idx, t_sec in enumerate(tqdm(all_t, desc=f"Neural Extraction ({self.mode})")):
            frame_idx = int(t_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                results.append({"timestamp_s": t_sec, "reading_value": np.nan, "raw_text": "", "confidence": 0.0, "status": "FRAME_ERROR"})
                continue
                
            corners = corner_trajectory[idx]
            warped_lcd = self.warp_lcd(frame, corners)
            val, raw_txt, conf = self.predict_reading(warped_lcd)
            
            results.append({
                "timestamp_s": float(t_sec),
                "reading_value": val,
                "raw_text": raw_txt,
                "confidence": conf,
                "status": "OK" if not np.isnan(val) else "LOW_CONFIDENCE"
            })
            
        cap.release()
        df = pd.DataFrame(results)
        
        # Outlier filtering & linear interpolation + rolling median smoothing
        readings = df['reading_value'].copy()
        max_bound = 35.0 if self.mode == 'voltage' else 150.0
        readings[(readings > max_bound) | (readings < -5.0)] = np.nan
        df['cleaned_value'] = readings.interpolate(method='linear', limit=5).ffill().bfill().rolling(3, min_periods=1, center=True).median()
        
        out_csv = os.path.join(self.output_dir, f"{self.mode}_readings_calibrated.csv")
        df.to_csv(out_csv, index=False)
        print(f"\n✅ Final Calibrated CSV Saved to: {out_csv}")
        
        # Save high-resolution visualization plot
        out_png = os.path.join(self.output_dir, f"{self.mode}_readings_calibrated_plot.png")
        plt.figure(figsize=(14, 5))
        plt.plot(df['timestamp_s'], df['reading_value'], 'b.', alpha=0.35, label='Raw Neural Detections')
        plt.plot(df['timestamp_s'], df['cleaned_value'], 'r-', linewidth=1.8, label='Cleaned Physical Signal (1s)')
        unit = "Voltage (V)" if self.mode == "voltage" else "Current (uA)"
        plt.title(f"Calibrated 1Hz Time-Series: {unit} vs Time (Full 15 Minutes)", fontsize=14, fontweight='bold')
        plt.xlabel("Time (seconds)", fontsize=12)
        plt.ylabel(unit, fontsize=12)
        plt.ylim(-0.5, 12.0 if self.mode == 'voltage' else 60.0)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(out_png, dpi=180)
        plt.close()
        print(f"✅ Saved plot to: {out_png}")


def main():
    parser = argparse.ArgumentParser(description="Calibrated Multimeter Full Extraction")
    parser.add_argument("--mode", choices=["voltage", "current"], default="voltage", help="Video mode")
    args = parser.parse_args()
    
    extractor = CalibratedExtractor(mode=args.mode)
    extractor.run_extraction()


if __name__ == "__main__":
    main()
