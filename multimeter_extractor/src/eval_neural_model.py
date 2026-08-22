import cv2
import numpy as np
import os
import json
import torch
import torch.nn as nn

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
LABELED_DIR = os.path.join(BASE_DIR, "labeled_data", "voltage")
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

def predict_crop(crop_img):
    h, w = crop_img.shape[:2]
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
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
            
        if pred_class != 10: # not blank
            digits.append((s_idx, str(pred_class)))

    if not digits:
        return ""
        
    num_str = "".join([d[1] for d in digits])
    
    # Auto-ranging decimal point logic for UNI-T UT33A+ in DC Volts mode:
    # 4 digits (e.g. 0452, 1018, 1351) -> 0.452, 1.018, 1.351 (3 decimal places)
    # 3 digits (e.g. 623, 205, 519)     -> 6.23, 2.05, 5.19   (2 decimal places)
    # 2 digits (e.g. 53)               -> 5.3                (1 decimal place)
    if len(num_str) == 4:
        formatted = f"{num_str[0]}.{num_str[1:]}"
    elif len(num_str) == 3:
        formatted = f"{num_str[0]}.{num_str[1:]}"
    elif len(num_str) == 2:
        formatted = f"{num_str[0]}.{num_str[1:]}"
    else:
        formatted = num_str
        
    return formatted

with open(os.path.join(LABELED_DIR, "annotations.json")) as f:
    annotations = json.load(f)

crops_dir = os.path.join(LABELED_DIR, "crops")
correct = 0
total = len(annotations)

print(f"{'Key':<10} | {'True Value':<10} | {'Neural Net Predicted':<20} | {'Match':<6}")
print("-" * 55)

for k, item in annotations.items():
    true_val = item["value"]
    crop_path = os.path.join(crops_dir, item["crop_file"])
    img = cv2.imread(crop_path)
    if img is not None:
        pred = predict_crop(img)
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
            
        print(f"{k:<10} | {true_val:<10} | {pred:<20} | {match_str}")

print("-" * 55)
print(f"🎯 Exact Accuracy on User Labeled Ground Truth: {correct}/{total} ({correct/total*100:.1f}%)")
