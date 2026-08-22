import cv2
import numpy as np

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames/Voltage_Readings__t0120s.jpg")
h, w = img.shape[:2]

# In t=120s, let's crop the multimeter
crop = img[50:1200, 1800:3000]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v120_crop.jpg", crop)
print("Saved v120_crop.")
