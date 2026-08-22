import cv2
import numpy as np

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames/Voltage_Readings__t0300s.jpg")
h, w = img.shape[:2]
print(f"Full 4K image size: {w}x{h}")

# The multimeter in Voltage_Readings__t0300s.jpg:
# Center is roughly x: 1000..1800, y: 300..1200
# Let's crop x: 900 to 1900, y: 200 to 1300
crop = img[200:1300, 900:1900]
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/v300_full_crop.jpg", crop)

print("Saved v300_full_crop.")
