import cv2
import numpy as np
import os
import glob

sample_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/multimeter_detector_test"
os.makedirs(out_dir, exist_ok=True)

def find_multimeter(image):
    """
    Finds the prominent red multimeter in the image and returns its rotated rect & corners.
    """
    h, w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Red has two hue ranges in HSV: [0, 15] and [165, 180]
    # S > 60, V > 40
    m1 = cv2.inRange(hsv, np.array([0, 60, 40]), np.array([15, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([165, 60, 40]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(m1, m2)
    
    # Close gaps
    k_size = int(max(h, w) * 0.015)
    k_size = max(5, k_size | 1)  # ensure odd
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
    cleaned = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_cnt = None
    max_area = 0
    min_area = (h * w) * 0.015  # At least 1.5% of the frame
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            # We prefer contours that have the aspect ratio of a multimeter (~1.5 to 2.2)
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (rw, rh), angle = rect
            if rw > 0 and rh > 0:
                aspect = max(rw, rh) / min(rw, rh)
                if 1.2 <= aspect <= 3.0:
                    if area > max_area:
                        max_area = area
                        best_cnt = cnt

    return best_cnt, cleaned

# Test on all sample images
for img_path in sorted(glob.glob(os.path.join(sample_dir, "*.jpg"))):
    img = cv2.imread(img_path)
    if img is None:
        continue
    
    cnt, mask = find_multimeter(img)
    vis = img.copy()
    
    if cnt is not None:
        rect = cv2.minAreaRect(cnt)
        box = np.int32(cv2.boxPoints(rect))
        cv2.drawContours(vis, [box], 0, (0, 255, 0), 4)
        (cx, cy), (rw, rh), angle = rect
        cv2.putText(vis, f"Multimeter found: {int(rw)}x{int(rh)}, {angle:.1f}deg", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    else:
        cv2.putText(vis, "Multimeter NOT found", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    
    base_name = os.path.basename(img_path)
    # Resize for quick inspection
    h, w = vis.shape[:2]
    scale = 800 / max(h, w)
    preview = cv2.resize(vis, (int(w * scale), int(h * scale)))
    cv2.imwrite(os.path.join(out_dir, f"det_{base_name}"), preview)

print("Detection test completed.")
