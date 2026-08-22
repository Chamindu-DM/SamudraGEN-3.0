import cv2
import numpy as np
import os

test_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/alignment_tests"
os.makedirs(out_dir, exist_ok=True)

# Let's test on Voltage t=300s (3840x2160)
img_v300 = cv2.imread(os.path.join(test_dir, "Voltage_Readings__t0300s.jpg"))
print("Loaded img_v300 shape:", img_v300.shape if img_v300 is not None else None)

# In img_v300, the multimeter is rotated around 145 degrees.
# Let's test finding the LCD screen corners or rotating and cropping
# In Voltage t=300s, let's find the red casing / LCD bounding region
