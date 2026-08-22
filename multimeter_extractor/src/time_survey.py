import cv2
import os

video_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos"
debug_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey"
os.makedirs(debug_dir, exist_ok=True)

for v_file in ["Current readings.mp4", "Voltage Readings .mp4"]:
    v_path = os.path.join(video_dir, v_file)
    cap = cv2.VideoCapture(v_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = int(total_frames / fps)
    
    safe_name = v_file.replace(" ", "_").replace(".mp4", "")
    
    # Sample every 60 seconds
    for sec in range(0, duration_sec, 60):
        frame_idx = int(sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            # Resize frame to manageable resolution for fast inspection
            h, w = frame.shape[:2]
            scale = 640 / max(h, w)
            preview = cv2.resize(frame, (int(w * scale), int(h * scale)))
            cv2.putText(preview, f"{safe_name} t={sec}s", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            out_path = os.path.join(debug_dir, f"{safe_name}_sec_{sec:04d}.jpg")
            cv2.imwrite(out_path, preview)
            
    cap.release()

print("Time survey extracted successfully.")
