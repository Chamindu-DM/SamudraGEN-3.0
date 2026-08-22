import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor

crop_path = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/crop_curr_t300.jpg"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops"

img = cv2.imread(crop_path)

# Let's define the 4 corners of the LCD glass (TL, TR, BR, BL)
# In crop_curr_t300:
# TL: (82, 38)
# TR: (240, 102)
# BR: (185, 222)
# BL: (30, 158)
pts_src = np.array([
    [82, 38],
    [240, 102],
    [185, 222],
    [30, 158]
], dtype=np.float32)

target_w, target_h = 240, 120
pts_dst = np.array([
    [0, 0],
    [target_w - 1, 0],
    [target_w - 1, target_h - 1],
    [0, target_h - 1]
], dtype=np.float32)

M = cv2.getPerspectiveTransform(pts_src, pts_dst)
warped = cv2.warpPerspective(img, M, (target_w, target_h))
cv2.imwrite(os.path.join(out_dir, "warped_lcd.jpg"), warped)

# Preprocess warped LCD
preprocessor = LCDPreprocessor(target_size=(target_w, target_h))
gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6,6))
enhanced = clahe.apply(gray)
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 10)

cv2.imwrite(os.path.join(out_dir, "warped_enhanced.jpg"), enhanced)
cv2.imwrite(os.path.join(out_dir, "warped_binary.jpg"), binary)

# Decode digits
ocr = SevenSegmentOCR(segment_thresh=0.20)
res, conf = ocr.parse_lcd_readout(binary)
print(f"Warped LCD readout: '{res}' (conf: {conf:.2f})")
