import cv2
import numpy as np
import os

crop_path = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/crop_curr_t300.jpg"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops"

img = cv2.imread(crop_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Contrast enhancement
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)

# Thresholding to get dark segments (which will be white in binary mask)
# Invert so black segments become 255 (white)
_, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Adaptive thresholding as comparison
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)

cv2.imwrite(os.path.join(out_dir, "test_gray.jpg"), gray)
cv2.imwrite(os.path.join(out_dir, "test_enhanced.jpg"), enhanced)
cv2.imwrite(os.path.join(out_dir, "test_otsu.jpg"), thresh)
cv2.imwrite(os.path.join(out_dir, "test_adaptive.jpg"), adaptive)

print("Saved binarized images.")
