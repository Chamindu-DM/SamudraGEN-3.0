import cv2
import numpy as np

img_v = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/voltage_full_t60.jpg")
h, w = img_v.shape[:2]

hsv_v = cv2.cvtColor(img_v, cv2.COLOR_BGR2HSV)
m1 = cv2.inRange(hsv_v, np.array([0, 60, 40]), np.array([15, 255, 255]))
m2 = cv2.inRange(hsv_v, np.array([165, 60, 40]), np.array([180, 255, 255]))
mask_v = cv2.bitwise_or(m1, m2)

# Opening with a solid kernel to erase wires
wire_remover = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
eroded = cv2.morphologyEx(mask_v, cv2.MORPH_OPEN, wire_remover)
# Re-close multimeter body
closed = cv2.morphologyEx(eroded, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (45, 45)))

contours_v, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
vis = img_v.copy()

for cnt in contours_v:
    area = cv2.contourArea(cnt)
    if area > 100000:
        rect = cv2.minAreaRect(cnt)
        (cx, cy), (rw, rh), angle = rect
        aspect = max(rw, rh) / (min(rw, rh) + 1e-5)
        solidity = area / (rw * rh + 1e-5)
        print(f"Candidate: center=({cx:.1f}, {cy:.1f}), size=({rw:.1f}, {rh:.1f}), aspect={aspect:.2f}, solidity={solidity:.2f}")
        
        box = np.int32(cv2.boxPoints(rect))
        cv2.drawContours(vis, [box], 0, (0, 255, 0), 4)

scale = 1200 / 3840
preview = cv2.resize(vis, (int(w * scale), int(h * scale)))
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/voltage_t60_wires_removed.jpg", preview)
print("Saved preview.")
