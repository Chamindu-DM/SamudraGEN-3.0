import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/lcd_v300_rot180.jpg")
h, w = img.shape[:2]

# LCD is in the top section
lcd_crop = img[0:int(h*0.42), int(w*0.18):int(w*0.82)]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_lcd_crop.jpg", lcd_crop)

gray = cv2.cvtColor(lcd_crop, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6,6))
enhanced = clahe.apply(gray)
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_enhanced.jpg", enhanced)
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_binary.jpg", binary)

ocr = SevenSegmentOCR()
res, conf = ocr.parse_lcd_readout(binary)
print(f"Voltage t=300s OCR Readout: '{res}' (confidence: {conf:.2f})")
