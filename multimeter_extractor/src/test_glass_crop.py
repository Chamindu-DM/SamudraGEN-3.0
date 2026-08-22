import cv2
import numpy as np

img = cv2.imread("multimeter_extractor/debug_frames/lcd_quad_133.jpg")
h, w = img.shape[:2]

# Crop exact grey LCD glass
glass = img[int(h*0.18):int(h*0.80), int(w*0.05):int(w*0.95)]
glass = cv2.resize(glass, (400, 180))
cv2.imwrite("multimeter_extractor/debug_frames/exact_glass_133.jpg", glass)
