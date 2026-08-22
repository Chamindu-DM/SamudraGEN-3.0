import cv2
import numpy as np
import os
import sys

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/screen_only.jpg", cv2.IMREAD_GRAYSCALE)
h, w = img.shape[:2]

# Remove top icons (Auto, APO, DC) by masking top 20% and far left 20%
clean_screen = img.copy()
clean_screen[0:int(h*0.18), :] = 0
clean_screen[:, 0:int(w*0.15)] = 0

# Vertical projection (sum along columns)
v_proj = np.sum(clean_screen > 0, axis=0)

# Find active columns
active = v_proj > (h * 0.15)

# Find contiguous blocks
blocks = []
in_block = False
start_x = 0

for x, val in enumerate(active):
    if val and not in_block:
        in_block = True
        start_x = x
    elif not val and in_block:
        in_block = False
        if (x - start_x) >= int(w * 0.05):  # Minimum digit width
            blocks.append((start_x, x))

if in_block and (w - start_x) >= int(w * 0.05):
    blocks.append((start_x, w))

print(f"Detected {len(blocks)} digit blocks via vertical projection:")
for i, (bx1, bx2) in enumerate(blocks):
    print(f"  Block {i}: x=[{bx1}, {bx2}], width={bx2-bx1}")
    digit_crop = clean_screen[:, bx1:bx2]
    cv2.imwrite(f"/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/auto_block_{i}.jpg", digit_crop)
