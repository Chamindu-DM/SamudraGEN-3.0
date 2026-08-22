import cv2
import numpy as np
import os

out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/perfect_crops"
os.makedirs(out_dir, exist_ok=True)

# Voltage video (4K, multimeter on left, tilted ~115 deg)
cap_v = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Voltage Readings .mp4")
fps_v = cap_v.get(cv2.CAP_PROP_FPS)

# Current video (1080p, multimeter on bottom, upright)
cap_c = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Current readings.mp4")
fps_c = cap_c.get(cv2.CAP_PROP_FPS)

test_seconds = [10, 30, 60, 90, 120, 180, 240, 300, 360, 420, 480, 540, 600, 720, 840, 900]

# For Voltage:
for s in test_seconds:
    cap_v.set(cv2.CAP_PROP_POS_FRAMES, int(s * fps_v))
    ret, frame = cap_v.read()
    if ret:
        h, w = frame.shape[:2]
        # In Voltage, find red casing with wire-removal
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 40, 30]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (45, 45)))
        
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            rect = cv2.minAreaRect(cnts[0])
            (cx, cy), (rw, rh), angle = rect
            
            # Determine orientation
            if rw < rh:
                rect_w, rect_h = rw, rh
                rot = angle
            else:
                rect_w, rect_h = rh, rw
                rot = angle + 90.0
                
            # For Voltage video, the top is rotated +180 deg
            rot = (rot + 180.0) % 360.0
            
            # Warp multimeter body to upright 320x480
            mw, mh = 320, 480
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
            
            # Extract clean LCD glass window (y: 11% to 35%, x: 20% to 80%)
            lcd_glass = mm_upright[int(mh*0.11):int(mh*0.35), int(mw*0.20):int(mw*0.80)]
            lcd_glass = cv2.resize(lcd_glass, (300, 120))
            cv2.imwrite(os.path.join(out_dir, f"v_lcd_t{s:04d}s.jpg"), lcd_glass)

cap_v.release()

# For Current:
for s in test_seconds:
    cap_c.set(cv2.CAP_PROP_POS_FRAMES, int(s * fps_c))
    ret, frame = cap_c.read()
    if ret:
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 40, 30]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35)))
        
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            rect = cv2.minAreaRect(cnts[0])
            (cx, cy), (rw, rh), angle = rect
            
            if rw < rh:
                rect_w, rect_h = rw, rh
                rot = angle
            else:
                rect_w, rect_h = rh, rw
                rot = angle + 90.0
                
            mw, mh = 320, 480
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
            
            lcd_glass = mm_upright[int(mh*0.11):int(mh*0.35), int(mw*0.20):int(mw*0.80)]
            lcd_glass = cv2.resize(lcd_glass, (300, 120))
            cv2.imwrite(os.path.join(out_dir, f"c_lcd_t{s:04d}s.jpg"), lcd_glass)

cap_c.release()

print("Perfect LCD crops extracted.")
