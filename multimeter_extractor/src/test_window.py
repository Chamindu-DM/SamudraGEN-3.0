import cv2
import numpy as np
import os

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/warped_lcd2.jpg")
h, w = img.shape[:2]

# Crop strictly inside the LCD glass window
lcd_window = img[22:96, 30:280]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/lcd_window.jpg", lcd_window)

# Grayscale & CLAHE
gray = cv2.cvtColor(lcd_window, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6,6))
enhanced = clahe.apply(gray)

# Threshold: digits are dark
binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 8)
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/window_binary.jpg", binary)

print("Saved lcd_window and window_binary.")
