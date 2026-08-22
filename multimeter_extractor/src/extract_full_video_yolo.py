#!/usr/bin/env python3
"""
Full Video YOLO Multimeter Extractor
Extracts 1Hz readings across the entire 15-minute video using fine-tuned YOLOv8.
"""

import cv2
import numpy as np
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from ultralytics import YOLO
from tqdm import tqdm

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
MODEL_PATH = os.path.join(BASE_DIR, "yolo_runs", "digit_detector", "weights", "best.pt")
ANN_FILE = os.path.join(BASE_DIR, "labeled_data", "voltage", "annotations.json")
OUT_DIR = os.path.join(BASE_DIR, "output_data")
os.makedirs(OUT_DIR, exist_ok=True)

CLASSES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'dot', 'minus']


def extract_full_video(mode="voltage"):
    v_path = VIDEO_PATH if mode == "voltage" else os.path.join(BASE_DIR, "input_videos", "Current readings.mp4")
    cap = cv2.VideoCapture(v_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open {v_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = int(total_frames / fps) if fps > 0 else 0
    
    model = YOLO(MODEL_PATH)
    
    with open(ANN_FILE, "r") as f:
        annotations = json.load(f)
        
    anchor_times = np.array([item["timestamp_s"] for item in annotations.values()])
    anchor_keys = list(annotations.keys())
    
    def get_corners(t_sec):
        sorted_times = sorted(anchor_times)
        if t_sec <= sorted_times[0]:
            k = anchor_keys[np.argmin(anchor_times)]
            return np.array(annotations[k]["corners"], dtype=np.float32)
        if t_sec >= sorted_times[-1]:
            k = anchor_keys[np.argmax(anchor_times)]
            return np.array(annotations[k]["corners"], dtype=np.float32)
            
        for i in range(len(sorted_times) - 1):
            t1, t2 = sorted_times[i], sorted_times[i+1]
            if t1 <= t_sec <= t2:
                alpha = (t_sec - t1) / (t2 - t1) if t2 > t1 else 0.0
                k1 = [k for k in anchor_keys if annotations[k]["timestamp_s"] == t1][0]
                k2 = [k for k in anchor_keys if annotations[k]["timestamp_s"] == t2][0]
                c1 = np.array(annotations[k1]["corners"], dtype=np.float32)
                c2 = np.array(annotations[k2]["corners"], dtype=np.float32)
                return (1.0 - alpha) * c1 + alpha * c2
                
        return np.array(annotations[anchor_keys[0]]["corners"], dtype=np.float32)

    def warp_lcd(frame, corners, target_w=400, target_h=180):
        src = np.array(corners, dtype=np.float32)
        dst = np.array([[0, 0], [target_w - 1, 0], [target_w - 1, target_h - 1], [0, target_h - 1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(frame, M, (target_w, target_h))

    results = []
    print(f"\n🚀 Running YOLOv8 Character Detection on {duration_s} seconds of {mode.upper()}...")
    
    for t_sec in tqdm(range(0, duration_s + 1), desc=f"YOLO Extraction ({mode})"):
        frame_idx = int(t_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            results.append({"timestamp_s": float(t_sec), "reading_value": np.nan, "raw_text": "", "confidence": 0.0})
            continue
            
        corners = get_corners(t_sec)
        lcd = warp_lcd(frame, corners)
        
        preds = model.predict(lcd, conf=0.15, verbose=False)[0]
        boxes = preds.boxes
        
        items = []
        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1 = float(box.xyxy[0][0].item())
            cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else str(cls_id)
            if cls_name != "dot":
                items.append((x1, cls_name, conf))
                
        items.sort(key=lambda x: x[0])
        digits = [item[1] for item in items]
        confs = [item[2] for item in items]
        num_str = "".join(digits)
        
        if len(num_str) in [2, 3, 4]:
            val_str = f"{num_str[0]}.{num_str[1:]}"
        else:
            val_str = num_str
            
        try:
            val = float(val_str)
            avg_conf = float(np.mean(confs)) if confs else 0.0
            results.append({"timestamp_s": float(t_sec), "reading_value": val, "raw_text": val_str, "confidence": round(avg_conf, 3)})
        except Exception:
            results.append({"timestamp_s": float(t_sec), "reading_value": np.nan, "raw_text": val_str, "confidence": 0.0})

    cap.release()
    df = pd.DataFrame(results)
    
    # Filter outliers and smooth
    readings = df['reading_value'].copy()
    max_bound = 35.0 if mode == 'voltage' else 150.0
    readings[(readings > max_bound) | (readings < -5.0)] = np.nan
    df['cleaned_value'] = readings.interpolate(method='linear', limit=5).ffill().bfill().rolling(3, min_periods=1, center=True).median()
    
    out_csv = os.path.join(OUT_DIR, f"{mode}_readings_yolo.csv")
    df.to_csv(out_csv, index=False)
    print(f"✅ Saved YOLO Extracted CSV to: {out_csv}")
    
    # Save Plot
    out_png = os.path.join(OUT_DIR, f"{mode}_readings_yolo_plot.png")
    plt.figure(figsize=(14, 5))
    plt.plot(df['timestamp_s'], df['reading_value'], 'b.', alpha=0.35, label='Raw YOLO Detections')
    plt.plot(df['timestamp_s'], df['cleaned_value'], 'r-', linewidth=1.8, label='Cleaned Physical Signal (1s)')
    unit = "Voltage (V)" if mode == "voltage" else "Current (uA)"
    plt.title(f"YOLOv8 Extracted 1Hz Time-Series: {unit} vs Time (Full 15 Minutes)", fontsize=14, fontweight='bold')
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel(unit, fontsize=12)
    plt.ylim(-0.5, 12.0 if mode == 'voltage' else 60.0)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close()
    print(f"✅ Saved YOLO Plot to: {out_png}")


if __name__ == "__main__":
    extract_full_video("voltage")
