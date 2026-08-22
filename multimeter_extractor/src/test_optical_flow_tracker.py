import cv2
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

def test_lk_tracker(video_path, initial_corners, start_sec=60, duration=15, name="lk_test"):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    out_dir = f"/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/{name}"
    os.makedirs(out_dir, exist_ok=True)
    
    # Seek to start frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_sec * fps))
    ret, prev_frame = cap.read()
    if not ret:
        print("Failed to read start frame")
        return
        
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    
    # Points to track around the LCD
    corners = np.array(initial_corners, dtype=np.float32).reshape(-1, 1, 2)
    
    # Target warp size
    target_w, target_h = 320, 160
    dst_pts = np.array([
        [0, 0],
        [target_w - 1, 0],
        [target_w - 1, target_h - 1],
        [0, target_h - 1]
    ], dtype=np.float32)
    
    # Extract good features inside the bounding box of corners for robust LK flow
    x_min, y_min = np.min(corners[:, 0, :], axis=0)
    x_max, y_max = np.max(corners[:, 0, :], axis=0)
    
    # Expand bbox slightly
    pad = 50
    h, w = prev_frame.shape[:2]
    mask = np.zeros_like(prev_gray)
    cv2.rectangle(mask, (max(0, int(x_min - pad)), max(0, int(y_min - pad))),
                  (min(w - 1, int(x_max + pad)), min(h - 1, int(y_max + pad))), 255, -1)
                  
    p0 = cv2.goodFeaturesToTrack(prev_gray, mask=mask, maxCorners=100, qualityLevel=0.01, minDistance=7)
    
    current_corners = corners.copy()
    
    for s in range(start_sec, start_sec + duration):
        frame_idx = int(s * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
            
        cur_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(prev_gray, cur_gray, p0, None, winSize=(25, 25), maxLevel=3)
        
        good_p0 = p0[st == 1]
        good_p1 = p1[st == 1]
        
        if len(good_p1) >= 4:
            # Estimate affine/homography transform
            H, inliers = cv2.estimateAffinePartial2D(good_p0, good_p1)
            if H is not None:
                current_corners = cv2.transform(corners, H)
                
        # Warp LCD
        M_warp = cv2.getPerspectiveTransform(current_corners.reshape(4, 2), dst_pts)
        warped = cv2.warpPerspective(frame, M_warp, (target_w, target_h))
        
        # Save warped LCD
        cv2.imwrite(os.path.join(out_dir, f"warped_{s:04d}s.jpg"), warped)
        
        # Visual overlay
        vis = frame.copy()
        cv2.polylines(vis, [np.int32(current_corners.reshape(4, 2))], isClosed=True, color=(0, 255, 0), thickness=3)
        scale = 720 / max(h, w)
        vis_small = cv2.resize(vis, (int(w * scale), int(h * scale)))
        cv2.imwrite(os.path.join(out_dir, f"track_{s:04d}s.jpg"), vis_small)
        
        prev_gray = cur_gray
        p0 = good_p1.reshape(-1, 1, 2)
        corners = current_corners.copy()
        
    cap.release()
    print(f"Tracking test finished for {name}.")

# Initial corners for Current readings at t=60s (h=1920, w=1080)
# Let's inspect t=60s for Current readings
