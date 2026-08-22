import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/warped_binary2.jpg", cv2.IMREAD_GRAYSCALE)

# Crop inner screen to eliminate bezel border
inner = img[18:100, 25:295]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/screen_only.jpg", inner)

ocr = SevenSegmentOCR(segment_thresh=0.20)

# Let's test single digit decoding for '5' and '3'
# In screen_only (h=82, w=270):
# '5' is roughly x: 170 to 215, y: 5 to 75
# '3' is roughly x: 220 to 265, y: 5 to 75
d5 = inner[5:75, 170:215]
d3 = inner[5:75, 220:265]

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d5.jpg", d5)
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/d3.jpg", d3)

c5, conf5 = ocr.decode_single_digit(d5)
c3, conf3 = ocr.decode_single_digit(d3)
print(f"Digit 1: '{c5}' (conf: {conf5:.2f})")
print(f"Digit 2: '{c3}' (conf: {conf3:.2f})")
