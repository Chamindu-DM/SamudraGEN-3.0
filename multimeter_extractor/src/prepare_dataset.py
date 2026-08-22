#!/usr/bin/env python3
"""
High-Resolution LCD Frame Crop Extractor & Dataset Packager
Extracts high-resolution upright LCD crops for every second of the multimeter videos
and bundles them into a clean zip archive for Google Colab or local deep learning inference.
"""

import cv2
import numpy as np
import os
import sys
import zipfile
from tqdm import tqdm

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_multimeter_lcd(frame, mode='voltage', target_w=600, target_h=240):
    """
    Detects the red UNI-T UT33A+ casing and extracts the high-resolution upright LCD screen.
    """
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Red silicone casing mask
    m1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([165, 40, 30]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(m1, m2)
    
    # Remove thin probe wires via morphological opening
    k_size = int(max(h, w) * 0.007) | 1
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size)))
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k_size * 3, k_size * 3)))
    
    cnts, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
        
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    best_cnt = cnts[0]
    if cv2.contourArea(best_cnt) < (h * w * 0.005):
        return None
        
    rect = cv2.minAreaRect(best_cnt)
    (cx, cy), (rw, rh), angle = rect
    
    if rw < rh:
        rect_w, rect_h = rw, rh
        rot = angle
    else:
        rect_w, rect_h = rh, rw
        rot = angle + 90.0
        
    # High-resolution upright bounding box (600x900)
    mw, mh = 600, 900
    src_pts = np.array([
        [cx - rect_w * 0.46, cy - rect_h * 0.48],
        [cx + rect_w * 0.46, cy - rect_h * 0.48],
        [cx + rect_w * 0.46, cy + rect_h * 0.48],
        [cx - rect_w * 0.46, cy + rect_h * 0.48]
    ], dtype=np.float32)
    
    M_rot = cv2.getRotationMatrix2D((cx, cy), -rot, 1.0)
    src_orig = cv2.transform(src_pts.reshape(1, -1, 2), M_rot).reshape(-1, 2)
    
    dst_pts = np.array([[0, 0], [mw - 1, 0], [mw - 1, mh - 1], [0, mh - 1]], dtype=np.float32)
    M_warp = cv2.getPerspectiveTransform(src_orig, dst_pts)
    mm_upright = cv2.warpPerspective(frame, M_warp, (mw, mh))
    
    # Extract clean LCD display window (y: 11% to 35%, x: 18% to 82%)
    lcd_glass = mm_upright[int(mh * 0.11):int(mh * 0.35), int(mw * 0.18):int(mw * 0.82)]
    lcd_glass_hd = cv2.resize(lcd_glass, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    
    return lcd_glass_hd


def extract_video_frames(video_path, output_dir, mode='voltage', sample_rate_hz=1.0):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}")
        return 0
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps if fps > 0 else 0
    timestamps = np.arange(0, duration_s, 1.0 / sample_rate_hz)
    
    print(f"[{mode.upper()}] Extracting {len(timestamps)} 1Hz LCD frames from {os.path.basename(video_path)}...")
    
    last_valid_crop = None
    saved_count = 0
    
    for t_sec in tqdm(timestamps, desc=f"Cropping {mode}"):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
        ret, frame = cap.read()
        if not ret:
            continue
            
        crop = extract_multimeter_lcd(frame, mode=mode)
        if crop is not None:
            last_valid_crop = crop
        else:
            crop = last_valid_crop
            
        if crop is not None:
            out_filename = os.path.join(output_dir, f"{mode}_t{int(t_sec):04d}s.jpg")
            cv2.imwrite(out_filename, crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_count += 1
            
    cap.release()
    print(f"[{mode.upper()}] Successfully saved {saved_count} frames to {output_dir}")
    return saved_count


def create_dataset_zip(dataset_dir, zip_output_path):
    print(f"\nCompressing dataset into {zip_output_path}...")
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dataset_dir):
            for file in files:
                if file.endswith(('.jpg', '.png', '.csv')):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, dataset_dir)
                    zipf.write(abs_path, rel_path)
                    
    zip_size_mb = os.path.getsize(zip_output_path) / (1024 * 1024)
    print(f"Dataset archive created! Size: {zip_size_mb:.2f} MB")


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(base_dir, "input_videos")
    dataset_dir = os.path.join(base_dir, "dataset")
    
    v_video = os.path.join(input_dir, "Voltage Readings .mp4")
    c_video = os.path.join(input_dir, "Current readings.mp4")
    
    v_out = os.path.join(dataset_dir, "voltage_frames")
    c_out = os.path.join(dataset_dir, "current_frames")
    
    if os.path.exists(v_video):
        extract_video_frames(v_video, v_out, mode='voltage')
        
    if os.path.exists(c_video):
        extract_video_frames(c_video, c_out, mode='current')
        
    zip_out = os.path.join(base_dir, "multimeter_lcd_dataset.zip")
    create_dataset_zip(dataset_dir, zip_out)
    print("\nDataset preparation complete! Ready for Google Colab / YOLO inference.")


if __name__ == "__main__":
    main()
