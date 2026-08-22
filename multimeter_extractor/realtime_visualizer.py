#!/usr/bin/env python3
"""
Real-Time Interactive Multimeter Inspection GUI
Allows live scrubbing, play/pause, step-by-step frame inspection,
and displays live YOLO character bounding boxes and readings.
"""

import cv2
import numpy as np
import os
import json
import argparse
from ultralytics import YOLO

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(REPO_ROOT, "multimeter_extractor")
VIDEO_PATH = os.path.join(BASE_DIR, "input_videos", "Voltage Readings .mp4")
MODEL_PATH = os.path.join(BASE_DIR, "yolo_runs", "digit_detector", "weights", "best.pt")
ANN_FILE = os.path.join(BASE_DIR, "labeled_data", "voltage", "annotations.json")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "saved_snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

CLASSES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'dot', 'minus']


class RealtimeMultimeterVisualizer:
    def __init__(self, video_path=VIDEO_PATH, model_path=MODEL_PATH, mode="voltage"):
        self.mode = mode
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"Could not open video at {video_path}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_s = int(self.total_frames / self.fps) if self.fps > 0 else 0
        
        # Load YOLO model
        if not os.path.exists(model_path):
            print(f"⚠️ Warning: Model not found at {model_path}. Loading base model.")
            self.model = YOLO("multimeter_extractor/yolov8n.pt")
        else:
            self.model = YOLO(model_path)
            
        # Load corner anchors
        with open(ANN_FILE, "r") as f:
            self.annotations = json.load(f)
            
        self.anchor_times = np.array([item["timestamp_s"] for item in self.annotations.values()])
        self.anchor_keys = list(self.annotations.keys())
        
        self.current_sec = 120
        self.is_paused = True
        self.window_name = f"Real-Time Multimeter Inspection - {mode.upper()}"

    def get_interpolated_corners(self, t_sec):
        # Find 2 nearest anchors for smooth corner positioning
        sorted_times = sorted(self.anchor_times)
        if t_sec <= sorted_times[0]:
            k = self.anchor_keys[np.argmin(self.anchor_times)]
            return np.array(self.annotations[k]["corners"], dtype=np.float32)
        if t_sec >= sorted_times[-1]:
            k = self.anchor_keys[np.argmax(self.anchor_times)]
            return np.array(self.annotations[k]["corners"], dtype=np.float32)
            
        # Find bounding bracket
        for i in range(len(sorted_times) - 1):
            t1, t2 = sorted_times[i], sorted_times[i+1]
            if t1 <= t_sec <= t2:
                alpha = (t_sec - t1) / (t2 - t1) if t2 > t1 else 0.0
                k1 = [k for k in self.anchor_keys if self.annotations[k]["timestamp_s"] == t1][0]
                k2 = [k for k in self.anchor_keys if self.annotations[k]["timestamp_s"] == t2][0]
                c1 = np.array(self.annotations[k1]["corners"], dtype=np.float32)
                c2 = np.array(self.annotations[k2]["corners"], dtype=np.float32)
                return (1.0 - alpha) * c1 + alpha * c2
                
        return np.array(self.annotations[self.anchor_keys[0]]["corners"], dtype=np.float32)

    def warp_lcd(self, frame, corners, target_w=400, target_h=180):
        src = np.array(corners, dtype=np.float32)
        dst = np.array([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1]
        ], dtype=np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(frame, M, (target_w, target_h))

    def detect_and_parse_reading(self, lcd_img):
        results = self.model.predict(lcd_img, conf=0.25, verbose=False)[0]
        boxes = results.boxes
        
        detected_items = []
        annotated_lcd = lcd_img.copy()
        
        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else str(cls_id)
            
            x1, y1, x2, y2 = xyxy
            detected_items.append({
                "x1": x1,
                "x2": x2,
                "cls": cls_name,
                "conf": conf,
                "box": (x1, y1, x2, y2)
            })
            
            # Draw box on annotated LCD
            color = (0, 255, 0) if cls_name != 'dot' else (0, 255, 255)
            cv2.rectangle(annotated_lcd, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_lcd, f"{cls_name} {int(conf*100)}%", (x1, max(12, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        # Sort detected items left-to-right by x1
        detected_items.sort(key=lambda item: item["x1"])
        
        # Build reading string
        raw_str = ""
        has_dot = False
        for item in detected_items:
            ch = item["cls"]
            if ch == "dot":
                if not has_dot and raw_str:
                    raw_str += "."
                    has_dot = True
            elif ch == "minus":
                if not raw_str:
                    raw_str += "-"
            else:
                raw_str += ch
                
        # Auto-ranging fallback if dot wasn't explicitly detected as a box
        if "." not in raw_str and len(raw_str.lstrip('-')) in [2, 3, 4]:
            clean = raw_str.lstrip('-')
            raw_str = f"{clean[0]}.{clean[1:]}"
            if raw_str.startswith('-'):
                raw_str = f"-{raw_str}"
                
        return raw_str, annotated_lcd, detected_items

    def render_dashboard(self, frame, t_sec):
        disp_w, disp_h = 1280, 720
        canvas = cv2.resize(frame, (disp_w, disp_h))
        
        corners = self.get_interpolated_corners(t_sec)
        h, w = frame.shape[:2]
        scale_x, scale_y = disp_w / w, disp_h / h
        
        pts_disp = np.array([[int(px * scale_x), int(py * scale_y)] for px, py in corners], np.int32)
        cv2.polylines(canvas, [pts_disp], isClosed=True, color=(0, 255, 0), thickness=2)
        
        # Warp & detect
        warped_lcd = self.warp_lcd(frame, corners)
        val_str, annotated_lcd, items = self.detect_and_parse_reading(warped_lcd)
        
        # Render Zoomed LCD Panel (top right)
        lcd_panel_w, lcd_panel_h = 360, 162
        lcd_thumb = cv2.resize(annotated_lcd, (lcd_panel_w, lcd_panel_h))
        
        cv2.rectangle(canvas, (disp_w - lcd_panel_w - 16, 12), (disp_w - 10, lcd_panel_h + 40), (20, 20, 20), -1)
        canvas[32:32+lcd_panel_h, disp_w - lcd_panel_w - 14:disp_w - 14] = lcd_thumb
        cv2.rectangle(canvas, (disp_w - lcd_panel_w - 14, 32), (disp_w - 14, 32+lcd_panel_h), (0, 255, 0), 2)
        cv2.putText(canvas, "LIVE YOLO DETECTIONS", (disp_w - lcd_panel_w - 10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
                    
        # Header banner
        cv2.rectangle(canvas, (0, 0), (disp_w - lcd_panel_w - 20, 64), (15, 15, 15), -1)
        cv2.putText(canvas, f"Time: {t_sec}s ({t_sec//60:02d}:{t_sec%60:02d}) / {self.duration_s}s",
                    (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                    
        unit = "V" if self.mode == "voltage" else "uA"
        val_display = f"{val_str} {unit}" if val_str else "Searching..."
        cv2.putText(canvas, f"Detected: {val_display}",
                    (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)
                    
        # Footer Help
        cv2.rectangle(canvas, (0, disp_h - 32), (disp_w, disp_h), (10, 10, 10), -1)
        status_text = "PAUSED (Press SPACE to Play)" if self.is_paused else "PLAYING (Press SPACE to Pause)"
        cv2.putText(canvas, f"[{status_text}]  |  [A / D]: -1s / +1s  |  [S]: Save Snapshot  |  [Q]: Quit",
                    (16, disp_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    
        return canvas

    def on_trackbar(self, val):
        self.current_sec = min(self.duration_s, max(0, val))

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 720)
        cv2.createTrackbar("Time (s)", self.window_name, self.current_sec, self.duration_s, self.on_trackbar)
        
        print("\n" + "="*70)
        print(" 🔍 LAUNCHING REAL-TIME INTERACTIVE MULTIMETER VISUALIZER ")
        print("="*70)
        print(" Controls:")
        print("   • [SPACE]: Play / Pause")
        print("   • [A / D] or [Left / Right]: Step -1s / +1s")
        print("   • [Trackbar]: Drag slider to jump to any timestamp")
        print("   • [S]: Save snapshot image with detections")
        print("   • [Q / ESC]: Quit viewer\n")
        
        while True:
            frame_idx = int(self.current_sec * self.fps)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if not ret:
                break
                
            dashboard = self.render_dashboard(frame, self.current_sec)
            cv2.imshow(self.window_name, dashboard)
            cv2.setTrackbarPos("Time (s)", self.window_name, self.current_sec)
            
            wait_time = 30 if not self.is_paused else 0
            key = cv2.waitKey(wait_time if wait_time > 0 else 50) & 0xFF
            
            if key in [ord('q'), 27]: # Q or ESC
                break
            elif key == ord(' '): # Space
                self.is_paused = not self.is_paused
            elif key in [ord('d'), 83]: # D or Right arrow
                self.current_sec = min(self.duration_s, self.current_sec + 1)
            elif key in [ord('a'), 81]: # A or Left arrow
                self.current_sec = max(0, self.current_sec - 1)
            elif key == ord('s'): # Save snapshot
                snap_path = os.path.join(SNAPSHOT_DIR, f"snapshot_t{self.current_sec:04d}s.jpg")
                cv2.imwrite(snap_path, dashboard)
                print(f"📸 Saved snapshot to: {snap_path}")
                
            if not self.is_paused:
                self.current_sec = min(self.duration_s, self.current_sec + 1)
                if self.current_sec >= self.duration_s:
                    self.is_paused = True

        self.cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Real-Time Multimeter Visualizer")
    parser.add_argument("--mode", default="voltage", choices=["voltage", "current"])
    args = parser.parse_args()
    
    vis = RealtimeMultimeterVisualizer(mode=args.mode)
    vis.run()


if __name__ == "__main__":
    main()
