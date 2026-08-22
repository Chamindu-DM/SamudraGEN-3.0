import cv2
import numpy as np
import json
import os

with open("multimeter_extractor/labeled_data/voltage/annotations.json") as f:
    annotations = json.load(f)

crops_dir = "multimeter_extractor/labeled_data/voltage/crops"

# 7-Segment Boolean Truth Table
# Segments: A (top), B (top-right), C (bottom-right), D (bottom), E (bottom-left), F (top-left), G (middle)
DIGIT_MAP = {
    (1, 1, 1, 1, 1, 1, 0): '0',
    (0, 1, 1, 0, 0, 0, 0): '1',
    (1, 1, 0, 1, 1, 0, 1): '2',
    (1, 1, 1, 1, 0, 0, 1): '3',
    (0, 1, 1, 0, 0, 1, 1): '4',
    (1, 0, 1, 1, 0, 1, 1): '5',
    (1, 0, 1, 1, 1, 1, 1): '6',
    (1, 1, 1, 0, 0, 0, 0): '7',
    (1, 1, 1, 1, 1, 1, 1): '8',
    (1, 1, 1, 1, 0, 1, 1): '9',
    (1, 1, 1, 0, 0, 1, 1): '9',
}

# The 4 fixed digit slot x-ranges (relative to 400x180 crop):
# Digit 1: x in [0.13, 0.33]
# Digit 2: x in [0.35, 0.55]
# Digit 3: x in [0.57, 0.77]
# Digit 4: x in [0.78, 0.98]
# Y-range for digits: [0.22, 0.94]
slot_boxes = [
    (0.13, 0.33),
    (0.35, 0.55),
    (0.57, 0.77),
    (0.78, 0.98)
]

def decode_crop(crop_img):
    h, w = crop_img.shape[:2]
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    
    # Bilateral filter to smooth water droplets while keeping sharp segment edges
    denoised = cv2.bilateralFilter(gray, 7, 50, 50)
    
    # Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Binarize with Otsu on digit zone
    digit_zone = enhanced[int(h*0.22):int(h*0.94), int(w*0.13):int(w*0.98)]
    thresh_val, _ = cv2.threshold(digit_zone, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, binary = cv2.threshold(enhanced, float(thresh_val), 255, cv2.THRESH_BINARY_INV)
    
    # Segments relative to each digit slot
    seg_samples = {
        'A': (0.24, 0.34, 0.20, 0.80), # top
        'B': (0.33, 0.55, 0.65, 0.98), # top-right
        'C': (0.60, 0.82, 0.65, 0.98), # bot-right
        'D': (0.82, 0.93, 0.20, 0.80), # bot
        'E': (0.60, 0.82, 0.02, 0.35), # bot-left
        'F': (0.33, 0.55, 0.02, 0.35), # top-left
        'G': (0.52, 0.62, 0.20, 0.80), # mid
    }
    
    chars = []
    dp_after_slot = None
    
    for s_idx, (x1_f, x2_f) in enumerate(slot_boxes):
        sx1, sx2 = int(x1_f * w), int(x2_f * w)
        slot_roi = binary[:, sx1:sx2]
        
        # Check if slot has enough dark ink to be an active digit
        # Check middle area of slot
        mid_roi = binary[int(h*0.30):int(h*0.85), sx1:sx2]
        if np.mean(mid_roi > 128) < 0.06:
            # Slot is blank (e.g. leading space in 6.23)
            continue
            
        bits = []
        for seg in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            y1_f, y2_f, sx1_f, sx2_f = seg_samples[seg]
            y1, y2 = int(y1_f * h), int(y2_f * h)
            x1 = int(sx1 + sx1_f * (sx2 - sx1))
            x2 = int(sx1 + sx2_f * (sx2 - sx1))
            roi = binary[y1:y2, x1:x2]
            score = np.mean(roi > 128) if roi.size > 0 else 0
            bits.append(1 if score > 0.25 else 0)
            
        bt = tuple(bits)
        char = DIGIT_MAP.get(bt, None)
        
        if char is None:
            # Best distance match
            best_d = 99
            for p, ch in DIGIT_MAP.items():
                d = sum(abs(a - b) for a, b in zip(bt, p))
                if d < best_d and d <= 2:
                    best_d = d
                    char = ch
                    
        if char is not None:
            chars.append(char)
            # Check for decimal point on bottom right of this slot
            dp_roi = binary[int(h*0.80):int(h*0.96), int(sx2 - (sx2-sx1)*0.25):int(sx2 + (sx2-sx1)*0.08)]
            if np.mean(dp_roi > 128) > 0.12 and dp_after_slot is None and s_idx < 3:
                dp_after_slot = len(chars)
                
    if not chars:
        return ""
        
    out_str = ""
    for i, ch in enumerate(chars):
        out_str += ch
        if dp_after_slot is not None and (i + 1) == dp_after_slot:
            out_str += "."
            
    return out_str

# Test on all 24 labeled annotations
correct = 0
total = len(annotations)

print(f"{'Key':<10} | {'True Value':<10} | {'Predicted':<10} | {'Match':<6}")
print("-" * 45)

for k, item in annotations.items():
    true_val = item["value"]
    crop_path = os.path.join(crops_dir, item["crop_file"])
    img = cv2.imread(crop_path)
    if img is not None:
        pred = decode_crop(img)
        # Compare numeric equivalence
        is_match = False
        try:
            if float(pred) == float(true_val):
                is_match = True
        except Exception:
            is_match = (pred == true_val)
            
        if is_match:
            correct += 1
            match_str = "✅ YES"
        else:
            match_str = "❌ NO"
            
        print(f"{k:<10} | {true_val:<10} | {pred:<10} | {match_str}")

print("-" * 45)
print(f"Accuracy on User Labeled Keyframes: {correct}/{total} ({correct/total*100:.1f}%)")
