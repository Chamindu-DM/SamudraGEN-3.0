import cv2
import numpy as np

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/lcd_Voltage_Readings__t0300s.jpg")
h, w = img.shape[:2]

# If the multimeter was inverted, the LCD is at the bottom instead of top.
# Let's rotate 180 degrees:
rot_180 = cv2.rotate(img, cv2.ROTATE_180)
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/tracker_test/lcd_v300_rot180.jpg", rot_180)
print("Saved lcd_v300_rot180.")
