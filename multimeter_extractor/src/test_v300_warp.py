import cv2
import numpy as np
import os

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_lcd_crop.jpg")

# 4 corners of the LCD glass rectangle
src_pts = np.array([
    [32, 30],
    [165, 0],
    [215, 38],
    [82, 78]
], dtype=np.float32)

target_w, target_h = 300, 140
dst_pts = np.array([
    [0, 0],
    [target_w - 1, 0],
    [target_w - 1, target_h - 1],
    [0, target_h - 1]
], dtype=np.float32)

M = cv2.getPerspectiveTransform(src_pts, dst_pts)
warped = cv2.warpPerspective(img, M, (target_w, target_h))
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_warped.jpg", warped)

print("Saved v300_warped.")
