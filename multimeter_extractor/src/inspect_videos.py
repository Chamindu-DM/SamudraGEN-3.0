import cv2
import os
import json

video_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos"
debug_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
os.makedirs(debug_dir, exist_ok=True)

video_files = [
    "Current readings.mp4",
    "Voltage Readings .mp4"
]

results = {}

for v_file in video_files:
    v_path = os.path.join(video_dir, v_file)
    if not os.path.exists(v_path):
        print(f"File not found: {v_path}")
        continue
    
    cap = cv2.VideoCapture(v_path)
    if not cap.isOpened():
        print(f"Failed to open {v_path}")
        continue
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0
    
    results[v_file] = {
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_sec": duration_sec,
        "duration_min": duration_sec / 60.0
    }
    
    # Extract sample frames at various timestamps
    sample_timestamps = [1, 5, 10, 30, 60, 90, 120, 180, 240, 300]
    safe_name = v_file.replace(" ", "_").replace(".mp4", "")
    
    for sec in sample_timestamps:
        if sec >= duration_sec:
            break
        frame_idx = int(sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            out_path = os.path.join(debug_dir, f"{safe_name}_t{sec:04d}s.jpg")
            cv2.imwrite(out_path, frame)
            
    cap.release()

print(json.dumps(results, indent=2))
