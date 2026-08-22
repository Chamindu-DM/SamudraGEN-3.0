"""
Multimeter and LCD Screen Tracker
Handles camera drift, shake, and perspective changes across video frames with temporal memory.
"""

import cv2
import numpy as np


class MultimeterTracker:
    def __init__(self, mode='voltage'):
        self.mode = mode.lower()
        self.last_rect = None
        self.last_corners = None
        self.last_cx = None
        self.last_cy = None
        self.last_w = None
        self.last_h = None

    def detect_multimeter(self, frame):
        """
        Detects the red UNI-T multimeter body using HSV color segmentation,
        aspect ratio filtering, and temporal memory tracking.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Red silicone casing mask (generous ranges to handle low light & flash)
        m1 = cv2.inRange(hsv, np.array([0, 35, 25]), np.array([22, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([155, 35, 25]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(m1, m2)
        
        # Wire removal via opening
        k_wire = int(max(h, w) * 0.007) | 1
        mask_clean = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k_wire, k_wire)))
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k_wire * 3, k_wire * 3)))
        
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        min_area = (h * w) * 0.005
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                rect = cv2.minAreaRect(cnt)
                (cx, cy), (rw, rh), angle = rect
                if rw > 0 and rh > 0:
                    aspect = max(rw, rh) / min(rw, rh)
                    if 1.15 <= aspect <= 3.5:
                        score = area
                        # If we have previous position, boost score based on proximity
                        if self.last_cx is not None:
                            dist = np.hypot(cx - self.last_cx, cy - self.last_cy)
                            score = area / (1.0 + dist * 0.005)
                        candidates.append((score, rect, cnt))
                        
        if candidates:
            candidates.sort(key=lambda c: c[0], reverse=True)
            best_score, best_rect, best_cnt = candidates[0]
            
            (cx, cy), (rw, rh), angle = best_rect
            self.last_rect = best_rect
            self.last_cx = cx
            self.last_cy = cy
            self.last_w = rw
            self.last_h = rh
            box = np.float32(cv2.boxPoints(best_rect))
            return best_rect, box

        # If color detection failed on this frame (e.g. shadow or flash dip), use temporal memory
        if self.last_rect is not None:
            box = np.float32(cv2.boxPoints(self.last_rect))
            return self.last_rect, box

        return None, None

    def extract_lcd_roi(self, frame, multimeter_rect, target_w=320, target_h=160):
        """
        Given the multimeter rotated rectangle, extracts and rectifies the LCD screen.
        """
        (cx, cy), (rw, rh), angle = multimeter_rect
        
        # Determine orientation
        if rw < rh:
            rect_w, rect_h = rw, rh
            rot_angle = angle
        else:
            rect_w, rect_h = rh, rw
            rot_angle = angle + 90.0

        if self.mode == "voltage":
            rot_angle = (rot_angle + 180.0) % 360.0

        # Warp multimeter to standard upright box (320x480)
        mw, mh = 320, 480
        src_upright = np.array([
            [cx - rect_w * 0.46, cy - rect_h * 0.48],
            [cx + rect_w * 0.46, cy - rect_h * 0.48],
            [cx + rect_w * 0.46, cy + rect_h * 0.48],
            [cx - rect_w * 0.46, cy + rect_h * 0.48]
        ], dtype=np.float32)

        M_rot = cv2.getRotationMatrix2D((cx, cy), -rot_angle, 1.0)
        src_orig = cv2.transform(src_upright.reshape(1, -1, 2), M_rot).reshape(-1, 2)

        dst_pts = np.array([
            [0, 0],
            [mw - 1, 0],
            [mw - 1, mh - 1],
            [0, mh - 1]
        ], dtype=np.float32)

        M_warp = cv2.getPerspectiveTransform(src_orig, dst_pts)
        upright_mm = cv2.warpPerspective(frame, M_warp, (mw, mh))

        # Crop LCD region (y: 8% to 38%, x: 18% to 82%)
        lcd_crop = upright_mm[int(mh * 0.08):int(mh * 0.38), int(mw * 0.18):int(mw * 0.82)]
        lcd_crop_resized = cv2.resize(lcd_crop, (target_w, target_h))

        return lcd_crop_resized, src_orig
