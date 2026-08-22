import cv2
import numpy as np
import os
import torch
import torch.nn as nn

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
MODEL_PATH = os.path.join(BASE_DIR, "digit_cnn.pt")

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

def find_inner_lcd_quad(casing_crop):
    """
    Finds the exact 4 corners of the grey inner LCD screen inside the casing crop.
    """
    h, w = casing_crop.shape[:2]
    gray = cv2.cvtColor(casing_crop, cv2.COLOR_BGR2GRAY)
    
    # In casing_crop, the LCD glass is brighter than the black plastic bezel surrounding it
    # Otsu thresholding on the upper half
    upper = gray[int(h*0.08):int(h*0.45), int(w*0.12):int(w*0.88)]
    thresh, bin_img = cv2.threshold(upper, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Clean binary mask of LCD glass
    mask = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)[1]
    mask[:int(h*0.08), :] = 0
    mask[int(h*0.45):, :] = 0
    mask[:, :int(w*0.12)] = 0
    mask[:, int(w*0.88):] = 0
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        # Fallback to fixed ratio
        return casing_crop[int(h*0.13):int(h*0.35), int(w*0.18):int(w*0.82)]
        
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    rect = cv2.minAreaRect(cnts[0])
    box = cv2.boxPoints(rect)
    
    # Order points: TL, TR, BR, BL
    pts = np.zeros((4, 2), dtype=np.float32)
    s = box.sum(axis=1)
    pts[0] = box[np.argmin(s)]
    pts[2] = box[np.argmax(s)]
    diff = np.diff(box, axis=1)
    pts[1] = box[np.argmin(diff)]
    pts[3] = box[np.argmax(diff)]
    
    target_w, target_h = 400, 180
    dst = np.array([[0,0], [target_w-1, 0], [target_w-1, target_h-1], [0, target_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(casing_crop, M, (target_w, target_h))
    return warped

def decode_lcd(lcd_img):
    h, w = lcd_img.shape[:2]
    gray = cv2.cvtColor(lcd_img, cv2.COLOR_BGR2GRAY)
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

# Test on t=133
cap = cv2.VideoCapture(os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)

# Let's extract multimeter casing
cap.set(cv2.CAP_PROP_POS_FRAMES, int(133 * fps))
ret, frame = cap.read()
if ret:
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([165, 40, 30]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(m1, m2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (45, 45)))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
    casing = cv2.warpPerspective(frame, M_warp, (mw, mh))
    
    lcd_quad = find_inner_lcd_quad(casing)
    cv2.imwrite("multimeter_extractor/debug_frames/lcd_quad_133.jpg", lcd_quad)
    pred = decode_lcd(lcd_quad)
    print(f"t=133s True: 2.62 | Predicted: {pred}")

cap.release()
