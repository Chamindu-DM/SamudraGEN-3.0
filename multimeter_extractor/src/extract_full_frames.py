#!/usr/bin/env python3
"""
Full-Resolution Frame Extractor (1Hz)
Extracts 100% full-resolution, uncropped video frames for each second (t=0..900s).
Voltage: 3840x2160 (4K)
Current: 1080x1920 (HD)
"""

import cv2
import numpy as np
import os
import sys
from tqdm import tqdm

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_dir = os.path.join(base_dir, "input_videos")
output_base = os.path.join(base_dir, "dataset_full_frames")


def extract_full_video_frames(video_path, output_dir, mode='voltage', sample_rate_hz=1.0):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening {video_path}")
        return 0
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps if fps > 0 else 0
    timestamps = np.arange(0, duration_s, 1.0 / sample_rate_hz)
    
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[{mode.upper()}] Extracting {len(timestamps)} uncropped full frames ({w}x{h}) from {os.path.basename(video_path)}...")
    
    count = 0
    for t_sec in tqdm(timestamps, desc=f"Full Frames {mode}"):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
        ret, frame = cap.read()
        if not ret:
            continue
            
        out_name = os.path.join(output_dir, f"{mode}_full_t{int(t_sec):04d}s.jpg")
        cv2.imwrite(out_name, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        count += 1
        
    cap.release()
    print(f"[{mode.upper()}] Saved {count} full frames to {output_dir}")
    return count


def main():
    v_video = os.path.join(input_dir, "Voltage Readings .mp4")
    c_video = os.path.join(input_dir, "Current readings.mp4")
    
    v_out = os.path.join(output_base, "voltage_full_frames")
    c_out = os.path.join(output_base, "current_full_frames")
    
    if os.path.exists(v_video):
        extract_full_video_frames(v_video, v_out, mode='voltage')
        
    if os.path.exists(c_video):
        extract_full_video_frames(c_video, c_out, mode='current')

    print("\n✅ All full-resolution frames extracted!")


if __name__ == "__main__":
    main()
