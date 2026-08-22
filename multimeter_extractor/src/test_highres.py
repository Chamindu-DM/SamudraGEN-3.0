import cv2
import numpy as np

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_full_crop.jpg")

# 4 corners
src_pts = np.array([
    [735, 155],
    [930, 365],
    [690, 565],
    [495, 360]
], dtype=np.float32)

target_w, target_h = 600, 280
dst_pts = np.array([
    [0, 0],
    [target_w - 1, 0],
    [target_w - 1, target_h - 1],
    [0, target_h - 1]
], dtype=np.float32)

M = cv2.getPerspectiveTransform(src_pts, dst_pts)
warped = cv2.warpPerspective(img, M, (target_w, target_h))
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_highres.jpg", warped)

# Preprocess
gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8)

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_highres_binary.jpg", binary)
print("Saved highres.")
