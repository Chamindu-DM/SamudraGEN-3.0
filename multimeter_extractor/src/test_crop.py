import cv2
import numpy as np
import os

# Let's crop the LCD screen from media_1787337841317.jpg
user_img_path = "/Users/chamindu/.gemini/antigravity/brain/03eda759-e49c-4efc-9d5a-bafae6315bc9/.user_uploaded/media_1787337841317.jpg"
out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops"
os.makedirs(out_dir, exist_ok=True)

img = cv2.imread(user_img_path)
if img is not None:
    h, w = img.shape[:2]
    # The LCD in media_1787337841317.jpg is roughly in the top-right multimeter
    # Let's crop various candidate regions or save the full image with grid
    cv2.imwrite(os.path.join(out_dir, "test_user_img2.jpg"), img)

# Let's also check Current_readings_t0300s.jpg
img_curr = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames/Current_readings_t0300s.jpg")
if img_curr is not None:
    # In Current_readings_t0300s.jpg (h=1920, w=1080):
    # Multimeter is in lower-left: y roughly 1000:1800, x roughly 100:600
    # LCD is in upper part of multimeter: y roughly 1100:1350, x roughly 230:520
    crop = img_curr[1100:1350, 230:520]
    cv2.imwrite(os.path.join(out_dir, "crop_curr_t300.jpg"), crop)

print("Saved test crops.")
