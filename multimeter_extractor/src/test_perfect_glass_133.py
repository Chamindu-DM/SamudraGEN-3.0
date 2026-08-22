import cv2
import numpy as np
import torch
import torch.nn as nn

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
model.load_state_dict(torch.load("multimeter_extractor/digit_cnn.pt"))
model.eval()

img = cv2.imread("multimeter_extractor/debug_frames/lcd_quad_133.jpg")
h, w = img.shape[:2]

# The actual glass is strictly from y=12% to y=52% of lcd_quad_133
glass = img[int(h*0.10):int(h*0.50), int(w*0.06):int(w*0.94)]
glass = cv2.resize(glass, (400, 180))
cv2.imwrite("multimeter_extractor/debug_frames/perfect_glass_133.jpg", glass)

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

num_str = "".join(digits)
if len(num_str) in [2, 3, 4]:
    val_str = f"{num_str[0]}.{num_str[1:]}"
else:
    val_str = num_str

print(f"t=133s Extracted Digits: {digits} | Final Value: {val_str} V (Expected: 2.62 V)")
