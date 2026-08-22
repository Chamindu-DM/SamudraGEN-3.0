#!/usr/bin/env python3
"""
Custom PyTorch Multimeter Digit & Decimal Neural Network
Trained directly on human-labeled frames with synthetic droplet/lighting augmentations.
100% offline, native PyTorch, zero external network downloads.
"""

import cv2
import numpy as np
import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
LABELED_DIR = os.path.join(BASE_DIR, "labeled_data", "voltage")
MODEL_PATH = os.path.join(BASE_DIR, "digit_cnn.pt")

# Slots definition for 400x180 LCD crop
SLOT_BOUNDS = [
    (0.14, 0.33),  # Slot 0
    (0.36, 0.55),  # Slot 1
    (0.58, 0.77),  # Slot 2
    (0.79, 0.98),  # Slot 3
]
DIGIT_Y = (0.24, 0.94)

# Classes: 0-9 (0..9), Blank (10)
NUM_CLASSES = 11


class MultimeterDigitCNN(nn.Module):
    def __init__(self):
        super(MultimeterDigitCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 64x48 -> 32x24

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 32x24 -> 16x12

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 16x12 -> 8x6
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(128 * 8 * 6, 128),
            nn.ReLU(),
            nn.Linear(128, NUM_CLASSES)
        )

    def forward(self, x):
        feat = self.features(x)
        feat = feat.view(feat.size(0), -1)
        out = self.classifier(feat)
        return out


def extract_slots_and_labels(crop_img, val_str):
    """
    Extracts the 4 slot image patches (64x48) and their ground-truth class IDs (0..10)
    along with the decimal point position.
    """
    h, w = crop_img.shape[:2]
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    clean = val_str.lstrip('-')
    parts = clean.split('.')
    whole = parts[0]
    frac = parts[1] if len(parts) > 1 else ""
    digits = whole + frac
    
    total_digits = len(digits)
    if total_digits == 4:
        start_slot = 0
    elif total_digits == 3:
        start_slot = 1
    elif total_digits == 2:
        start_slot = 2
    else:
        start_slot = 4 - total_digits
        
    slots_data = []
    dp_slot_idx = (start_slot + len(whole) - 1) if len(parts) > 1 else None
    
    for s_idx, (x1_f, x2_f) in enumerate(SLOT_BOUNDS):
        sx1, sx2 = int(x1_f * w), int(x2_f * w)
        sy1, sy2 = int(DIGIT_Y[0] * h), int(DIGIT_Y[1] * h)
        slot_patch = enhanced[sy1:sy2, sx1:sx2]
        slot_patch = cv2.resize(slot_patch, (48, 64))
        
        # Determine label
        if s_idx < start_slot or (s_idx - start_slot) >= len(digits):
            label = 10 # Blank
        else:
            ch = digits[s_idx - start_slot]
            label = int(ch)
            
        slots_data.append((slot_patch, label))
        
    return slots_data, dp_slot_idx


class AugmentedDigitDataset(Dataset):
    def __init__(self, samples, num_augmentations=30):
        self.data = []
        for patch, label in samples:
            # Add base sample
            norm = (patch.astype(np.float32) / 255.0 - 0.5) / 0.5
            self.data.append((torch.tensor(norm, dtype=torch.float32).unsqueeze(0), label))
            
            # Generate augmentations (lighting, water streaks, blur, noise)
            for _ in range(num_augmentations):
                aug = patch.copy()
                # Contrast/Brightness
                alpha = np.random.uniform(0.7, 1.4)
                beta = np.random.uniform(-30, 30)
                aug = np.clip(alpha * aug.astype(np.float32) + beta, 0, 255).astype(np.uint8)
                
                # Random water drop
                if np.random.rand() > 0.4:
                    rx = np.random.randint(5, 40)
                    ry = np.random.randint(5, 55)
                    rr = np.random.randint(3, 10)
                    cv2.circle(aug, (rx, ry), rr, (230,), -1)
                    
                # Random blur
                if np.random.rand() > 0.5:
                    aug = cv2.GaussianBlur(aug, (3, 3), 0)
                    
                aug_norm = (aug.astype(np.float32) / 255.0 - 0.5) / 0.5
                self.data.append((torch.tensor(aug_norm, dtype=torch.float32).unsqueeze(0), label))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]


def train_digit_model():
    with open(os.path.join(LABELED_DIR, "annotations.json")) as f:
        annotations = json.load(f)
        
    crops_dir = os.path.join(LABELED_DIR, "crops")
    all_slot_samples = []
    
    for k, item in annotations.items():
        val_str = item["value"]
        crop_path = os.path.join(crops_dir, item["crop_file"])
        img = cv2.imread(crop_path)
        if img is None:
            continue
        slots, _ = extract_slots_and_labels(img, val_str)
        all_slot_samples.extend(slots)
        
    print(f"Collected {len(all_slot_samples)} base slot samples from human-labeled keyframes.")
    dataset = AugmentedDigitDataset(all_slot_samples, num_augmentations=40)
    print(f"Generated {len(dataset)} augmented training samples with water/lighting variations.")
    
    loader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    device = torch.device("cpu")
    model = MultimeterDigitCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    
    print("\n🚀 Training Deep Neural Network...")
    model.train()
    for epoch in range(15):
        total_loss = 0.0
        correct = 0
        total = 0
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
            
        acc = correct / total * 100.0
        if (epoch + 1) % 3 == 0 or epoch == 14:
            print(f"  Epoch [{epoch+1:02d}/15] | Loss: {total_loss/len(loader):.4f} | Training Accuracy: {acc:.2f}%")
            
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"\n🎉 Model training complete! Saved neural weights to: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_digit_model()
