import cv2
import numpy as np

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames/Voltage_Readings__t0120s.jpg")
h, w = img.shape[:2]

# Center left in 4K
crop = img[0:1600, 1500:2600]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v120_full.jpg", crop)
print("Saved v120_full.")
