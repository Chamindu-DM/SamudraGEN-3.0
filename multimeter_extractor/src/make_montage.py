import cv2
import numpy as np
import os
import glob

# Let's inspect survey frames for both videos
survey_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey"
debug_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/survey_analysis"
os.makedirs(debug_dir, exist_ok=True)

# Generate a grid montage for Current readings and Voltage readings
for prefix in ["Current_readings", "Voltage_Readings_"]:
    files = sorted(glob.glob(os.path.join(survey_dir, f"{prefix}_sec_*.jpg")))
    imgs = [cv2.imread(f) for f in files if cv2.imread(f) is not None]
    
    if not imgs:
        continue
    
    # Resize all to same thumbnail size
    thumb_w, thumb_h = 320, 240
    thumbs = [cv2.resize(img, (thumb_w, thumb_h)) for img in imgs]
    
    # Arrange in grid (e.g. 4 columns)
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    
    # Pad to grid size with black images
    while len(thumbs) < rows * cols:
        thumbs.append(np.zeros((thumb_h, thumb_w, 3), dtype=np.uint8))
        
    grid_rows = []
    for r in range(rows):
        row_imgs = thumbs[r*cols : (r+1)*cols]
        grid_rows.append(np.hstack(row_imgs))
        
    montage = np.vstack(grid_rows)
    cv2.imwrite(os.path.join(debug_dir, f"{prefix}_montage.jpg"), montage)

print("Montages created.")
