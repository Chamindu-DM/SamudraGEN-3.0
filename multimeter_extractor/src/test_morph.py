import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

crop_path = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/crop_curr_t300.jpg"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops"

img = cv2.imread(crop_path)
# Let's rotate by -22 degrees to make it horizontal
h, w = img.shape[:2]
center = (w // 2, h // 2)
M_rot = cv2.getRotationMatrix2D(center, -22.0, 1.0)
rotated = cv2.warpAffine(img, M_rot, (w, h))
cv2.imwrite(os.path.join(out_dir, "test_rotated.jpg"), rotated)

# Now crop the horizontal inner LCD display
# In rotated:
# Let's view rotated or find bounding box of LCD glass
gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 12)

# Morphological bridge to connect segments of the same digit
bridge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
bridged = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, bridge_kernel)

cv2.imwrite(os.path.join(out_dir, "test_rotated_binary.jpg"), binary)
cv2.imwrite(os.path.join(out_dir, "test_bridged.jpg"), bridged)

print("Saved rotated and bridged images.")
