import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor

preprocessor = LCDPreprocessor(target_size=(320, 160))
ocr = SevenSegmentOCR(segment_thresh=0.25)

crop_path = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/crop_curr_t300.jpg"
img = cv2.imread(crop_path)

# Let's inspect the inner LCD screen area (the greenish-grey rectangle)
# In crop_curr_t300: h=250, w=290
# The LCD glass is roughly y: 40 to 200, x: 50 to 270
h, w = img.shape[:2]
lcd_inner = img[int(h*0.15):int(h*0.85), int(w*0.18):int(w*0.95)]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/inner_lcd.jpg", lcd_inner)

enhanced = preprocessor.enhance_contrast(lcd_inner)
binary = preprocessor.binarize(enhanced)
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/inner_binary.jpg", binary)

# Parse with 7-segment OCR
readout, conf = ocr.parse_lcd_readout(binary)
print(f"Parsed LCD readout: '{readout}' with confidence {conf:.2f}")

# Also test decode_single_digit on extracted components
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Found {len(contours)} contours in binary LCD")
for i, cnt in enumerate(contours):
    x, y, bw, bh = cv2.boundingRect(cnt)
    if bh > binary.shape[0] * 0.3:
        digit_crop = binary[y:y+bh, x:x+bw]
        char, d_conf = ocr.decode_single_digit(digit_crop)
        print(f"  Contour {i} at x={x}, y={y}, w={bw}, h={bh} -> Char: '{char}' (conf: {d_conf:.2f})")
