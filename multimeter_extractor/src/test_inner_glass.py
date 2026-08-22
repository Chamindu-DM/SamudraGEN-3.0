import cv2
import numpy as np
import os
import json
import torch
import torch.nn as nn

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
MODEL_PATH = os.path.join(BASE_DIR, "digit_cnn.pt")

GROUND_TRUTH = {
    120: 1.571,
    121: 1.358,
    122: 1.212,
    123: 1.099,
    124: 1.007,
    125: 0.929,
    126: 0.863,
    127: 0.805,
    128: 0.756,
    129: 1.742,
    130: 2.86,
    131: 5.05,
    132: 4.19,
    133: 2.62
}

SLOT_BOUNDS = [
    (0.14, 0.33),  # Slot 0
    (0.36, 0.55),  # Slot 1
    (0.58, 0.77),  # Slot 2
    (0.79, 0.98),  # Slot 3
]
DIGIT_Y = (0.24, 0.94)

class MultimeterDigitCNN(nn.Module):
    def __init__(self):
        super(MultimeterDigitCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(128 * 8 * 6, 128),
            nn.ReLU(),
            nn.Linear(128, 11)
        )

    def forward(self, x):
        feat = self.features(x)
        feat = feat.view(feat.size(0), -1)
        out = self.classifier(feat)
        return out

model = MultimeterDigitCNN()
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()

def extract_inner_glass(frame):
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([165, 40, 30]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(m1, m2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (45, 45)))
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    rect = cv2.minAreaRect(cnts[0])
    (cx, cy), (rw, rh), angle = rect
    
    if rw < rh:
        rect_w, rect_h = rw, rh
        rot = angle
    else:
        rect_w, rect_h = rh, rw
        rot = angle + 90.0
        
    mw, mh = 400, 600
    src_pts = np.array([
        [cx - rect_w * 0.46, cy - rect_h * 0.48],
        [cx + rect_w * 0.46, cy - rect_h * 0.48],
        [cx + rect_w * 0.46, cy + rect_h * 0.48],
        [cx - rect_w * 0.46, cy + rect_h * 0.48]
    ], dtype=np.float32)
    
    M_rot = cv2.getRotationMatrix2D((cx, cy), -rot, 1.0)
    src_orig = cv2.transform(src_pts.reshape(1, -1, 2), M_rot).reshape(-1, 2)
    
    dst_pts = np.array([[0,0], [mw-1, 0], [mw-1, mh-1], [0, mh-1]], dtype=np.float32)
    M_warp = cv2.getPerspectiveTransform(src_orig, dst_pts)
    mm_upright = cv2.warpPerspective(frame, M_warp, (mw, mh))
    
    # Extract EXACT inner glass window matching user labeled crops (y: 15% to 32%, x: 21% to 79%)
    glass = mm_upright[int(mh*0.145):int(mh*0.325), int(mw*0.21):int(mw*0.79)]
    glass_resized = cv2.resize(glass, (400, 180))
    return glass_resized

def decode_glass(glass_img):
    h, w = glass_img.shape[:2]
    gray = cv2.cvtColor(glass_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    digits = []
    for s_idx, (x1_f, x2_f) in enumerate(SLOT_BOUNDS):
        sx1, sx2 = int(x1_f * w), int(x2_f * w)
        sy1, sy2 = int(DIGIT_Y[0] * h), int(DIGIT_Y[1] * h)
        patch = enhanced[sy1:sy2, sx1:sx2]
        patch_resized = cv2.resize(patch, (48, 64))
        
        norm = (patch_resized.astype(np.float32) / 255.0 - 0.5) / 0.5
        t_img = torch.tensor(norm, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        
        with torch.no_grad():
            out = model(t_img)
            pred_class = torch.argmax(out, dim=1).item()
            
        if pred_class != 10:
            digits.append(str(pred_class))

    if not digits:
        return None
    num_str = "".join(digits)
    if len(num_str) in [2, 3, 4]:
        val_str = f"{num_str[0]}.{num_str[1:]}"
    else:
        val_str = num_str
    try:
        return float(val_str)
    except Exception:
        return None

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)

print("\n" + "="*60)
print(" 🎯 EXACT INNER GLASS BENCHMARK TEST (120s..133s) ")
print("="*60)
print(f"{'Time (s)':<10} | {'Human True Value':<18} | {'Model Predicted':<16} | {'Status':<6}")
print("-" * 60)

correct = 0
for t_sec, true_val in GROUND_TRUTH.items():
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
    ret, frame = cap.read()
    if not ret:
        continue
    glass = extract_inner_glass(frame)
    if glass is not None:
        cv2.imwrite(f"multimeter_extractor/debug_frames/glass_t{t_sec}.jpg", glass)
        pred_val = decode_glass(glass)
        is_match = (pred_val is not None and abs(pred_val - true_val) < 1e-3)
        if is_match:
            correct += 1
            status = "✅ MATCH"
        else:
            status = f"❌ (got {pred_val})"
        print(f"{t_sec:<10} | {true_val:<18} | {str(pred_val):<16} | {status}")

cap.release()
print("-" * 60)
print(f"Accuracy: {correct}/{len(GROUND_TRUTH)} ({correct/len(GROUND_TRUTH)*100:.1f}%)")
