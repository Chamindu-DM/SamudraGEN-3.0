#!/usr/bin/env python3
"""
Verification Frame Generator (Minute 2 to Minute 3: t=120s to t=180s)
Extracts frames for every second from 120s to 180s, draws the extracted LCD crop
and overlays the timestamp & predicted CSV reading directly on the image.
"""

import cv2
import numpy as np
import pandas as pd
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from multimeter_extractor.train_and_extract import CalibratedExtractor

BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
CSV_PATH = os.path.join(BASE_DIR, "output_data", "voltage_readings_calibrated.csv")
OUT_DIR = os.path.join(BASE_DIR, "verification_frames_min2_to_min3")

os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)
csv_map = dict(zip(df['timestamp_s'].astype(int), df['raw_text']))
cleaned_map = dict(zip(df['timestamp_s'].astype(int), df['cleaned_value']))

extractor = CalibratedExtractor(mode="voltage")

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration_s = int(total_frames / fps)

_, corner_trajectory = extractor.build_corner_trajectory(duration_s)

print(f"Extracting 60 verification frames for Minute 2 to Minute 3 (t=120s to 180s)...")

for t_sec in range(120, 181):
    frame_idx = int(t_sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        continue
        
    corners = corner_trajectory[t_sec]
    warped_lcd = extractor.warp_lcd(frame, corners, target_w=400, target_h=180)
    
    raw_val = csv_map.get(t_sec, "")
    clean_val = cleaned_map.get(t_sec, np.nan)
    val_disp = f"{raw_val} V" if raw_val else "N/A"
    
    # Resize frame for clean display (e.g. 1280x720)
    h, w = frame.shape[:2]
    disp_w, disp_h = 1280, 720
    frame_resized = cv2.resize(frame, (disp_w, disp_h))
    
    # Scale corner points for resized display
    scale_x, scale_y = disp_w / w, disp_h / h
    pts_disp = np.array([[int(px * scale_x), int(py * scale_y)] for px, py in corners], np.int32)
    cv2.polylines(frame_resized, [pts_disp], isClosed=True, color=(0, 255, 0), thickness=2)
    
    # Embed the zoomed-in rectified LCD preview in top-right corner
    lcd_thumb = cv2.resize(warped_lcd, (320, 144))
    cv2.rectangle(frame_resized, (disp_w - 330, 10), (disp_w - 6, 160), (0, 0, 0), -1)
    frame_resized[13:13+144, disp_w - 328:disp_w - 8] = lcd_thumb
    cv2.rectangle(frame_resized, (disp_w - 328, 13), (disp_w - 8, 13+144), (0, 255, 0), 2)
    cv2.putText(frame_resized, "ZOOMED LCD", (disp_w - 320, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    
    # Add header banner with Timestamp & CSV reading
    cv2.rectangle(frame_resized, (0, 0), (disp_w - 340, 60), (20, 20, 20), -1)
    cv2.putText(frame_resized, f"Time: {t_sec}s (Min {t_sec//60}:{t_sec%60:02d})", (20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame_resized, f"CSV Value: {val_disp} (Cleaned: {clean_val:.3f}V)", (350, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    # Save frame with informative filename
    clean_val_str = f"{raw_val}" if raw_val else "none"
    filename = f"sec_{t_sec:03d}_value_{clean_val_str}V.jpg"
    out_path = os.path.join(OUT_DIR, filename)
    cv2.imwrite(out_path, frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 95])

cap.release()
print(f"✅ Successfully created {len(os.listdir(OUT_DIR))} verification frames in:\n{OUT_DIR}")
