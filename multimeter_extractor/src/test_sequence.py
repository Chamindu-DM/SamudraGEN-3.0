import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor

def test_video_clip(video_path, start_sec=100, num_seconds=20, name="clip"):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    out_dir = f"/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/pipeline_{name}"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Testing {name} from t={start_sec}s to t={start_sec+num_seconds}s (FPS: {fps:.2f})")
    
    ocr = SevenSegmentOCR(segment_thresh=0.25)
    preprocessor = LCDPreprocessor(target_size=(320, 160))
    
    extracted_data = []
    
    for s in range(start_sec, start_sec + num_seconds):
        frame_idx = int(s * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
            
        # Save sample frame
        out_frame_path = os.path.join(out_dir, f"frame_{s:04d}s.jpg")
        # Resize for preview
        h, w = frame.shape[:2]
        scale = 720 / max(h, w)
        preview = cv2.resize(frame, (int(w * scale), int(h * scale)))
        cv2.imwrite(out_frame_path, preview)
        
    cap.release()
    print(f"Extracted frames for {name}")

test_video_clip(
    "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Current readings.mp4",
    start_sec=120,
    num_seconds=10,
    name="current"
)

test_video_clip(
    "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Voltage Readings .mp4",
    start_sec=120,
    num_seconds=10,
    name="voltage"
)
