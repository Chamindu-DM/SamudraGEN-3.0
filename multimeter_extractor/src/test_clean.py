import cv2
import numpy as np
import os
import sys

img = cv2.imread("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/screen_only.jpg", cv2.IMREAD_GRAYSCALE)
h, w = img.shape[:2]

# 1. Filter out components touching border or with small area
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(img)
clean = np.zeros_like(img)

for i in range(1, num_labels):
    area = stats[i, cv2.CC_STAT_AREA]
    bx = stats[i, cv2.CC_STAT_LEFT]
    by = stats[i, cv2.CC_STAT_TOP]
    bw = stats[i, cv2.CC_STAT_WIDTH]
    bh = stats[i, cv2.CC_STAT_HEIGHT]
    
    # Exclude components that span the whole width (border line) or are too small
    if bw > w * 0.7:
        continue
    if area < 15:
        continue
    # Exclude DC/Auto icons at top left
    if bx < w * 0.2 and by < h * 0.4:
        continue
        
    clean[labels == i] = 255

cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/clean_screen.jpg", clean)

# Now vertical projection
v_proj = np.sum(clean > 0, axis=0)
active = v_proj > 0

blocks = []
in_block = False
start_x = 0
for x, val in enumerate(active):
    if val and not in_block:
        in_block = True
        start_x = x
    elif not val and in_block:
        in_block = False
        if (x - start_x) >= 5:
            blocks.append((start_x, x))
if in_block and (w - start_x) >= 5:
    blocks.append((start_x, w))

print(f"Cleaned screen found {len(blocks)} blocks:")
for i, (bx1, bx2) in enumerate(blocks):
    print(f"  Block {i}: x=[{bx1}, {bx2}], w={bx2-bx1}")
    cv2.imwrite(f"/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/lcd_crops/block_{i}.jpg", clean[:, bx1:bx2])
