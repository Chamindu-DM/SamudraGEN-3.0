import cv2
import numpy as np

# In current_full_t60.jpg (1920x1080):
img_c = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/current_full_t60.jpg")

# Find red contours in current_full_t60
hsv_c = cv2.cvtColor(img_c, cv2.COLOR_BGR2HSV)
m1 = cv2.inRange(hsv_c, np.array([0, 50, 40]), np.array([15, 255, 255]))
m2 = cv2.inRange(hsv_c, np.array([165, 50, 40]), np.array([180, 255, 255]))
mask_c = cv2.bitwise_or(m1, m2)
mask_c = cv2.morphologyEx(mask_c, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))

contours_c, _ = cv2.findContours(mask_c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for cnt in contours_c:
    area = cv2.contourArea(cnt)
    if area > 50000:
        rect = cv2.minAreaRect(cnt)
        box = np.int32(cv2.boxPoints(rect))
        print(f"Current t60 multimeter rect: center={rect[0]}, size={rect[1]}, angle={rect[2]}")
        cv2.drawContours(img_c, [box], 0, (0, 255, 0), 4)

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/current_t60_det.jpg", img_c)

# In voltage_full_t60.jpg (2160x3840):
img_v = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/voltage_full_t60.jpg")
hsv_v = cv2.cvtColor(img_v, cv2.COLOR_BGR2HSV)
m1 = cv2.inRange(hsv_v, np.array([0, 50, 40]), np.array([15, 255, 255]))
m2 = cv2.inRange(hsv_v, np.array([165, 50, 40]), np.array([180, 255, 255]))
mask_v = cv2.bitwise_or(m1, m2)
mask_v = cv2.morphologyEx(mask_v, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35)))

contours_v, _ = cv2.findContours(mask_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for cnt in contours_v:
    area = cv2.contourArea(cnt)
    if area > 100000:
        rect = cv2.minAreaRect(cnt)
        box = np.int32(cv2.boxPoints(rect))
        print(f"Voltage t60 multimeter rect: center={rect[0]}, size={rect[1]}, angle={rect[2]}")
        cv2.drawContours(img_v, [box], 0, (0, 255, 0), 4)

# Resize for preview
scale_v = 1200 / 3840
img_v_small = cv2.resize(img_v, (int(3840 * scale_v), int(2160 * scale_v)))
cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/voltage_t60_det.jpg", img_v_small)
