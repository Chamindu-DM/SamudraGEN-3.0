import cv2
import numpy as np
import os
import json
from ultralytics import YOLO

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
MODEL_PATH = os.path.join(BASE_DIR, "yolo_runs", "digit_detector", "weights", "best.pt")
ANN_FILE = os.path.join(BASE_DIR, "labeled_data", "voltage", "annotations.json")

CLASSES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'dot', 'minus']

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

model = YOLO(MODEL_PATH)

with open(ANN_FILE, "r") as f:
    annotations = json.load(f)

anchor_times = np.array([item["timestamp_s"] for item in annotations.values()])
anchor_keys = list(annotations.keys())

def get_interpolated_corners(t_sec):
    sorted_times = sorted(anchor_times)
    if t_sec <= sorted_times[0]:
        k = anchor_keys[np.argmin(anchor_times)]
        return np.array(annotations[k]["corners"], dtype=np.float32)
    if t_sec >= sorted_times[-1]:
        k = anchor_keys[np.argmax(anchor_times)]
        return np.array(annotations[k]["corners"], dtype=np.float32)
        
    for i in range(len(sorted_times) - 1):
        t1, t2 = sorted_times[i], sorted_times[i+1]
        if t1 <= t_sec <= t2:
            alpha = (t_sec - t1) / (t2 - t1) if t2 > t1 else 0.0
            k1 = [k for k in anchor_keys if annotations[k]["timestamp_s"] == t1][0]
            k2 = [k for k in anchor_keys if annotations[k]["timestamp_s"] == t2][0]
            c1 = np.array(annotations[k1]["corners"], dtype=np.float32)
            c2 = np.array(annotations[k2]["corners"], dtype=np.float32)
            return (1.0 - alpha) * c1 + alpha * c2
            
    return np.array(annotations[anchor_keys[0]]["corners"], dtype=np.float32)

def warp_lcd(frame, corners, target_w=400, target_h=180):
    src = np.array(corners, dtype=np.float32)
    dst = np.array([[0,0], [target_w-1, 0], [target_w-1, target_h-1], [0, target_h-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(frame, M, (target_w, target_h))

def parse_yolo_reading(lcd_img):
    results = model.predict(lcd_img, conf=0.20, verbose=False)[0]
    boxes = results.boxes
    items = []
    
    for box in boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        x1 = float(box.xyxy[0][0].item())
        cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else str(cls_id)
        if cls_name != "dot":  # Filter digits
            items.append((x1, cls_name, conf))
            
    # Sort left-to-right
    items.sort(key=lambda x: x[0])
    digits = [item[1] for item in items]
    num_str = "".join(digits)
    
    # Decimal point rule
    if len(num_str) in [2, 3, 4]:
        val_str = f"{num_str[0]}.{num_str[1:]}"
    else:
        val_str = num_str
        
    try:
        return float(val_str), val_str
    except Exception:
        return None, val_str

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)

print("\n" + "="*65)
print(" 🎯 YOLOv8 CHARACTER DETECTOR BENCHMARK (120s..133s) ")
print("="*65)
print(f"{'Time (s)':<10} | {'Human True Value':<18} | {'YOLO Predicted':<16} | {'Status':<6}")
print("-" * 65)

correct = 0
for t_sec, true_val in GROUND_TRUTH.items():
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
    ret, frame = cap.read()
    if not ret:
        continue
    corners = get_interpolated_corners(t_sec)
    lcd = warp_lcd(frame, corners)
    pred_val, raw_txt = parse_yolo_reading(lcd)
    
    is_match = (pred_val is not None and abs(pred_val - true_val) < 1e-3)
    if is_match:
        correct += 1
        status = "✅ MATCH"
    else:
        status = f"❌ (got {pred_val})"
    print(f"{t_sec:<10} | {true_val:<18} | {str(pred_val):<16} | {status}")

cap.release()
print("-" * 65)
print(f"YOLOv8 Accuracy: {correct}/{len(GROUND_TRUTH)} ({correct/len(GROUND_TRUTH)*100:.1f}%)")
