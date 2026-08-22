import cv2
import numpy as np
import torch
import torch.nn as nn

SLOT_BOUNDS = [
    (0.18, 0.38),  # Slot 0
    (0.39, 0.58),  # Slot 1
    (0.59, 0.78),  # Slot 2
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
model.load_state_dict(torch.load("multimeter_extractor/digit_cnn.pt"))
model.eval()

img = cv2.imread("multimeter_extractor/debug_frames/padded_sift_t125.jpg")
h, w = img.shape[:2]

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
        
    print(f"Slot {s_idx} ({x1_f:.2f}..{x2_f:.2f}): Class {pred_class}")
    if pred_class != 10:
        digits.append(str(pred_class))

num_str = "".join(digits)
print(f"Total String: {num_str} (Expected: 0929 -> 0.929 V)")
