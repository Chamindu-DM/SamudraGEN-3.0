import cv2
import numpy as np
import os
import sys

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d5.jpg", cv2.IMREAD_GRAYSCALE)
h, w = img.shape[:2]

# Let's define segment sample points/boxes with slight slant compensation:
# A: top horizontal (y: 0..18%, x: 20..80%)
# B: top-right vertical (y: 15..45%, x: 65..100%)
# C: bottom-right vertical (y: 55..85%, x: 55..95%)
# D: bottom horizontal (y: 82..100%, x: 10..75%)
# E: bottom-left vertical (y: 55..85%, x: 0..40%)
# F: top-left vertical (y: 15..45%, x: 10..50%)
# G: middle horizontal (y: 42..58%, x: 15..80%)

seg_boxes = {
    'A': (0.00, 0.18, 0.20, 0.85),
    'B': (0.15, 0.45, 0.60, 0.95),
    'C': (0.55, 0.85, 0.55, 0.90),
    'D': (0.82, 1.00, 0.10, 0.80),
    'E': (0.55, 0.85, 0.05, 0.40),
    'F': (0.15, 0.45, 0.10, 0.45),
    'G': (0.42, 0.58, 0.15, 0.80),
}

vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

results = {}
for seg, (y1_f, y2_f, x1_f, x2_f) in seg_boxes.items():
    y1, y2 = int(y1_f * h), int(y2_f * h)
    x1, x2 = int(x1_f * w), int(x2_f * w)
    roi = img[y1:y2, x1:x2]
    score = np.mean(roi > 128) if roi.size > 0 else 0.0
    results[seg] = score
    
    color = (0, 255, 0) if score > 0.35 else (0, 0, 255)
    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
    cv2.putText(vis, seg, (x1+2, y1+12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d5_calib.jpg", vis)

print("Segment scores for '5':")
for seg, s in results.items():
    print(f"  {seg}: {s:.2f} ({'ON' if s > 0.35 else 'OFF'})")
