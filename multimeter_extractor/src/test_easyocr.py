import cv2
import easyocr
import time
import os
import numpy as np

reader = easyocr.Reader(['en'], gpu=False)

crop_path = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/crop_curr_t300.jpg"
img = cv2.imread(crop_path)

t0 = time.time()
# Run easyocr with allowlist
results = reader.readtext(img, allowlist='0123456789.-uAmVv')
t1 = time.time()

print(f"EasyOCR raw took {t1-t0:.3f}s: {results}")

# Also try on enhanced/preprocessed image
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
enh = clahe.apply(gray)
t0 = time.time()
results_enh = reader.readtext(enh, allowlist='0123456789.-')
t1 = time.time()
print(f"EasyOCR enhanced took {t1-t0:.3f}s: {results_enh}")
