import cv2
import numpy as np
import os
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
ANN_FILE = os.path.join(BASE_DIR, "labeled_data", "voltage", "annotations.json")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")

with open(ANN_FILE, "r") as f:
    annotations = json.load(f)

# The 14 human-verified readings from user
VERIFIED_120_133 = {
    120: "1.571",
    121: "1.358",
    122: "1.212",
    123: "1.099",
    124: "1.007",
    125: "0.929",
    126: "0.863",
    127: "0.805",
    128: "0.756",
    129: "1.742",
    130: "2.86",
    131: "5.05",
    132: "4.19",
    133: "2.62"
}

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)

# Use t=116s anchor to compute homography for each of the 14 frames
cap.set(cv2.CAP_PROP_POS_FRAMES, int(116 * fps))
_, ref_frame = cap.read()
ref_corners = annotations["t_0116s"]["corners"]

sift = cv2.SIFT_create(nfeatures=1000)
kp1, des1 = sift.detectAndCompute(ref_frame, None)
matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

crops_dir = os.path.join(BASE_DIR, "labeled_data", "voltage", "crops")

for t_sec, val_str in VERIFIED_120_133.items():
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t_sec * fps))
    ret, frame = cap.read()
    if not ret:
        continue
        
    kp2, des2 = sift.detectAndCompute(frame, None)
    matches = matcher.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    
    if len(good) >= 6:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is not None:
            pts = np.array(ref_corners, dtype=np.float32).reshape(-1, 1, 2)
            cur_corners = cv2.perspectiveTransform(pts, H).reshape(4, 2)
            
            target_w, target_h = 400, 180
            dst = np.array([[0,0], [target_w-1, 0], [target_w-1, target_h-1], [0, target_h-1]], dtype=np.float32)
            M = cv2.getPerspectiveTransform(cur_corners.astype(np.float32), dst)
            warped = cv2.warpPerspective(frame, M, (target_w, target_h))
            
            crop_filename = f"voltage_t_{t_sec:04d}s.jpg"
            cv2.imwrite(os.path.join(crops_dir, crop_filename), warped)
            
            key = f"t_{t_sec:04d}s"
            annotations[key] = {
                "timestamp_s": float(t_sec),
                "corners": cur_corners.tolist(),
                "value": val_str,
                "crop_file": crop_filename
            }
            print(f"Added verified frame t={t_sec}s: {val_str} V")

cap.release()

with open(ANN_FILE, "w") as f:
    json.dump(annotations, f, indent=2)

print(f"\n🎉 Successfully merged! Dataset now contains {len(annotations)} human-verified ground-truth keyframes.")
