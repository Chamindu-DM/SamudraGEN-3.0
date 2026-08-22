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

# Load human-labeled anchor at t=116s as reference template
with open("multimeter_extractor/labeled_data/voltage/annotations.json") as f:
    ann = json.load(f)
anchor_116 = ann["t_0116s"]["corners"]

def extract_template_matched_lcd(frame, cap, fps):
    # Anchor at 116s
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(116 * fps))
    ret, ref_frame = cap.read()
    
    # SIFT feature matcher on multimeter region
    sift = cv2.SIFT_create(nfeatures=1000)
    kp1, des1 = sift.detectAndCompute(ref_frame, None)
    kp2, des2 = sift.detectAndCompute(frame, None)
    
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
    matches = flann.knnMatch(des1, des2, k=2)
    
    good = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good.append(m)
            
    if len(good) >= 8:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is not None:
            # Transform the 4 corners of t=116s anchor to current frame!
            pts_116 = np.array(anchor_116, dtype=np.float32).reshape(-1, 1, 2)
            cur_corners = cv2.perspectiveTransform(pts_116, H).reshape(4, 2)
            
            # Warp to flat LCD
            target_w, target_h = 400, 180
            dst = np.array([[0,0], [target_w-1, 0], [target_w-1, target_h-1], [0, target_h-1]], dtype=np.float32)
            M = cv2.getPerspectiveTransform(cur_corners, dst)
            warped = cv2.warpPerspective(frame, M, (target_w, target_h))
            return warped, cur_corners

    return None, None

def decode_lcd(glass):
    gray = cv2.cvtColor(glass, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    digits = []
    for s_idx, (x1_f, x2_f) in enumerate(SLOT_BOUNDS):
        sx1, sx2 = int(x1_f * 400), int(x2_f * 400)
        sy1, sy2 = int(DIGIT_Y[0] * 180), int(DIGIT_Y[1] * 180)
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

print("\n" + "="*65)
print(" 🎯 SIFT-HOMOGRAPHY ANCHOR MATCHING BENCHMARK (120s..133s) ")
print("="*65)
print(f"{'Time (s)':<10} | {'Human True Value':<18} | {'Model Predicted':<16} | {'Status':<6}")
print("-" * 65)

correct = 0
for t_sec, true_val in GROUND_TRUTH.items():
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
    ret, frame = cap.read()
    if not ret:
        continue
    glass, _ = extract_template_matched_lcd(frame, cap, fps)
    if glass is not None:
        cv2.imwrite(f"multimeter_extractor/debug_frames/sift_glass_t{t_sec}.jpg", glass)
        pred_val = decode_lcd(glass)
        is_match = (pred_val is not None and abs(pred_val - true_val) < 1e-3)
        if is_match:
            correct += 1
            status = "✅ MATCH"
        else:
            status = f"❌ (got {pred_val})"
        print(f"{t_sec:<10} | {true_val:<18} | {str(pred_val):<16} | {status}")

cap.release()
print("-" * 65)
print(f"SIFT Homography Accuracy: {correct}/{len(GROUND_TRUTH)} ({correct/len(GROUND_TRUTH)*100:.1f}%)")
