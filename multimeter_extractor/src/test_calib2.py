import cv2
import numpy as np
import os

def test_digit(img_path, name):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    h, w = img.shape[:2]
    
    seg_boxes = {
        'A': (0.00, 0.16, 0.15, 0.85),
        'B': (0.12, 0.45, 0.70, 1.00),
        'C': (0.52, 0.85, 0.70, 1.00),
        'D': (0.84, 1.00, 0.15, 0.85),
        'E': (0.52, 0.85, 0.00, 0.30),
        'F': (0.12, 0.45, 0.00, 0.30),
        'G': (0.40, 0.58, 0.15, 0.85),
    }

    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    results = {}
    bits = []
    
    for seg in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        y1_f, y2_f, x1_f, x2_f = seg_boxes[seg]
        y1, y2 = int(y1_f * h), int(y2_f * h)
        x1, x2 = int(x1_f * w), int(x2_f * w)
        roi = img[y1:y2, x1:x2]
        score = np.mean(roi > 128) if roi.size > 0 else 0.0
        results[seg] = score
        is_on = score >= 0.28
        bits.append(1 if is_on else 0)
        
        color = (0, 255, 0) if is_on else (0, 0, 255)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
        cv2.putText(vis, seg, (x1+1, y1+10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    cv2.imwrite(f"/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/{name}_calib.jpg", vis)
    print(f"Results for {name}: bits={tuple(bits)}")
    for seg, s in results.items():
        print(f"  {seg}: {s:.2f}")

test_digit("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d5.jpg", "d5")
test_digit("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d3.jpg", "d3")
