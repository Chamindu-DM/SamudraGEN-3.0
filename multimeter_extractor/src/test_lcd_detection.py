import cv2
import numpy as np
import os
import glob

sample_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/detection_tests"
os.makedirs(out_dir, exist_ok=True)

images = glob.glob(os.path.join(sample_dir, "*.jpg"))

for img_path in sorted(images):
    img = cv2.imread(img_path)
    if img is None:
        continue
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Red mask (multimeter outer casing)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)
    
    # Morphological clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    red_mask_clean = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    
    # Find red multimeter contours
    contours, _ = cv2.findContours(red_mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    debug_vis = img.copy()
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > (img.shape[0] * img.shape[1] * 0.03): # at least 3% of image
            # Multimeter detected
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            cv2.drawContours(debug_vis, [box], 0, (0, 255, 0), 3)
            
    base_name = os.path.basename(img_path)
    cv2.imwrite(os.path.join(out_dir, f"red_det_{base_name}"), debug_vis)

print(f"Processed {len(images)} sample images.")
