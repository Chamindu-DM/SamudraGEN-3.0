import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.lcd_tracker import MultimeterTracker

sample_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test"
os.makedirs(out_dir, exist_ok=True)

tracker = MultimeterTracker()

test_files = [
    "Current_readings_t0010s.jpg",
    "Current_readings_t0120s.jpg",
    "Current_readings_t0300s.jpg",
    "Voltage_Readings__t0120s.jpg",
    "Voltage_Readings__t0300s.jpg"
]

for fname in test_files:
    img_path = os.path.join(sample_dir, fname)
    img = cv2.imread(img_path)
    if img is None:
        continue
        
    rect, box = tracker.detect_multimeter(img)
    if rect is not None:
        lcd_roi, pts_orig = tracker.extract_lcd_roi(img, rect)
        cv2.imwrite(os.path.join(out_dir, f"lcd_{fname}"), lcd_roi)
        
        # Draw on image
        vis = img.copy()
        cv2.drawContours(vis, [np.int32(box)], 0, (0, 255, 0), 4)
        cv2.drawContours(vis, [np.int32(pts_orig)], 0, (0, 0, 255), 4)
        
        h, w = vis.shape[:2]
        scale = 800 / max(h, w)
        preview = cv2.resize(vis, (int(w * scale), int(h * scale)))
        cv2.imwrite(os.path.join(out_dir, f"vis_{fname}"), preview)
        print(f"Processed {fname}: Multimeter detected.")
    else:
        print(f"Processed {fname}: Not detected.")
