import cv2
import numpy as np
import os

out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/orientation_inspection"
os.makedirs(out_dir, exist_ok=True)

# Let's inspect Voltage at t=10s, 60s, 120s, 180s, 240s, 300s, 400s, 500s, 600s
cap_v = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Voltage Readings .mp4")
fps_v = cap_v.get(cv2.CAP_PROP_FPS)

for sec in [10, 60, 120, 180, 240, 300, 450, 600, 750]:
    cap_v.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps_v))
    ret, frame = cap_v.read()
    if ret:
        # In 4K video (3840x2160), multimeter is roughly in x: 1000..2800, y: 100..1600
        # Let's find red region and crop closely
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 50, 30]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 50, 30]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
        
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            x, y, w, h = cv2.boundingRect(cnts[0])
            pad = 50
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(frame.shape[1], x + w + pad), min(frame.shape[0], y + h + pad)
            mm_crop = frame[y1:y2, x1:x2]
            cv2.imwrite(os.path.join(out_dir, f"voltage_raw_t{sec:04d}s.jpg"), mm_crop)
            
cap_v.release()

# Let's do the same for Current video
cap_c = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Current readings.mp4")
fps_c = cap_c.get(cv2.CAP_PROP_FPS)

for sec in [10, 60, 120, 180, 240, 300, 450, 600, 750]:
    cap_c.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps_c))
    ret, frame = cap_c.read()
    if ret:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 50, 30]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 50, 30]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
        
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            x, y, w, h = cv2.boundingRect(cnts[0])
            pad = 30
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(frame.shape[1], x + w + pad), min(frame.shape[0], y + h + pad)
            mm_crop = frame[y1:y2, x1:x2]
            cv2.imwrite(os.path.join(out_dir, f"current_raw_t{sec:04d}s.jpg"), mm_crop)
            
cap_c.release()

print("Saved raw multimeter crops.")
