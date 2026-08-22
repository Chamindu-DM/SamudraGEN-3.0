#!/usr/bin/env python3
"""
Interactive Multimeter LCD Corner Annotator & Human-in-the-Loop Labeler
Allows the user to click 4 corners of the LCD screen on a sample of frames
and input the true human-read value.
"""

import cv2
import numpy as np
import os
import json
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class InteractiveLabeler:
    def __init__(self, video_path, mode="voltage", num_samples=25, output_dir=None):
        self.video_path = video_path
        self.mode = mode
        self.num_samples = num_samples
        
        if output_dir is None:
            self.output_dir = os.path.join(REPO_ROOT, "multimeter_extractor", "labeled_data", mode)
        else:
            self.output_dir = output_dir
            
        os.makedirs(self.output_dir, exist_ok=True)
        self.crops_dir = os.path.join(self.output_dir, "crops")
        os.makedirs(self.crops_dir, exist_ok=True)
        
        self.annotations_file = os.path.join(self.output_dir, "annotations.json")
        self.annotations = self._load_existing_annotations()
        
        self.current_points = []
        self.display_scale = 1.0
        self.window_name = f"Annotator - {mode.upper()} (Click 4 LCD Corners: TL -> TR -> BR -> BL)"

    def _load_existing_annotations(self):
        if os.path.exists(self.annotations_file):
            try:
                with open(self.annotations_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_annotations(self):
        with open(self.annotations_file, "w") as f:
            json.dump(self.annotations, f, indent=2)
        print(f"\n💾 Saved {len(self.annotations)} annotations to: {self.annotations_file}")

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.current_points) < 4:
                # Convert from display scale to original frame coordinates
                orig_x = int(x / self.display_scale)
                orig_y = int(y / self.display_scale)
                self.current_points.append((orig_x, orig_y))

    def _warp_lcd(self, frame, pts, target_w=400, target_h=180):
        src = np.array(pts, dtype=np.float32)
        dst = np.array([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(frame, M, (target_w, target_h))
        return warped

    def run(self):
        if not os.path.exists(self.video_path):
            print(f"❌ Error: Video not found at {self.video_path}")
            return

        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_s = total_frames / fps if fps > 0 else 0

        # Sample timestamps evenly across video
        sample_timestamps = np.linspace(5, max(5, duration_s - 5), self.num_samples)
        
        print("\n" + "="*70)
        print(f" 🎯 INTERACTIVE LABELER: {self.mode.upper()} VIDEO ")
        print(f" Total Video Duration: {duration_s:.1f} seconds")
        print(f" Sampling {len(sample_timestamps)} diverse frames for labeling")
        print("="*70)
        print(" Instructions:")
        print(" 1. A window will open showing the video frame.")
        print(" 2. Click the 4 CORNERS of the LCD DISPLAY in this order:")
        print("    [1] Top-Left  ->  [2] Top-Right  ->  [3] Bottom-Right  ->  [4] Bottom-Left")
        print(" 3. Press 'r' to Reset clicks if you made a mistake.")
        print(" 4. Press 's' to Skip the frame.")
        print(" 5. Press 'q' to Quit and save progress.")
        print(" 6. After clicking 4 points, check the warped preview & type the true reading in the terminal!")
        print("="*70 + "\n")

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        for idx, t_sec in enumerate(sample_timestamps):
            t_key = f"t_{int(t_sec):04d}s"
            
            # Check if already labeled
            if t_key in self.annotations:
                print(f"[{idx+1}/{len(sample_timestamps)}] Frame at t={int(t_sec)}s already labeled ({self.annotations[t_key]['value']}). Skipping.")
                continue

            frame_idx = int(t_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            h, w = frame.shape[:2]
            # Calculate display scale to fit comfortably on screen (e.g. max 1280x800)
            max_disp_w, max_disp_h = 1200, 750
            self.display_scale = min(max_disp_w / w, max_disp_h / h, 1.0)
            disp_w = int(w * self.display_scale)
            disp_h = int(h * self.display_scale)

            self.current_points = []
            
            # If we have previous points, we can initialize with them as a helper
            prev_pts = None
            if self.annotations:
                last_key = list(self.annotations.keys())[-1]
                prev_pts = self.annotations[last_key].get("corners")

            while True:
                # Prepare display image
                disp_img = cv2.resize(frame, (disp_w, disp_h))
                
                # Draw instructions on top of image
                cv2.rectangle(disp_img, (0, 0), (disp_w, 45), (30, 30, 30), -1)
                corner_names = ["1. TOP-LEFT", "2. TOP-RIGHT", "3. BOTTOM-RIGHT", "4. BOTTOM-LEFT"]
                curr_step = corner_names[len(self.current_points)] if len(self.current_points) < 4 else "Ready! (Press Space/Enter)"
                cv2.putText(disp_img, f"Frame {idx+1}/{len(sample_timestamps)} (t={int(t_sec)}s) | Click: {curr_step} | 'r':Reset | 's':Skip | 'q':Quit",
                            (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

                # Draw clicked points
                for p_idx, (px, py) in enumerate(self.current_points):
                    dpx, dpy = int(px * self.display_scale), int(py * self.display_scale)
                    cv2.circle(disp_img, (dpx, dpy), 6, (0, 0, 255), -1)
                    cv2.putText(disp_img, str(p_idx + 1), (dpx + 8, dpy + 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Draw connecting polygon if 4 points are set
                if len(self.current_points) == 4:
                    pts_arr = np.array([[int(px * self.display_scale), int(py * self.display_scale)] for px, py in self.current_points], np.int32)
                    cv2.polylines(disp_img, [pts_arr], isClosed=True, color=(0, 255, 0), thickness=2)

                cv2.imshow(self.window_name, disp_img)
                key = cv2.waitKey(30) & 0xFF

                if key == ord('q'):
                    print("\nQuitting labeler. Progress saved.")
                    self._save_annotations()
                    cap.release()
                    cv2.destroyAllWindows()
                    return

                elif key == ord('r'):
                    self.current_points = []
                    print("🔄 Reset corner points for this frame.")

                elif key == ord('s'):
                    print(f"⏩ Skipped frame at t={int(t_sec)}s.")
                    break

                elif len(self.current_points) == 4:
                    # All 4 corners clicked! Show the rectified LCD preview
                    warped = self._warp_lcd(frame, self.current_points, target_w=400, target_h=180)
                    cv2.imshow("LCD Flat Preview (Check Orientation)", warped)
                    cv2.waitKey(100)

                    # Prompt user in terminal for the reading
                    print(f"\n[{idx+1}/{len(sample_timestamps)}] Frame at t={int(t_sec)}s:")
                    print("  👉 Check the 'LCD Flat Preview' window.")
                    user_val = input(f"  👉 Enter human-read value (e.g. 0.708 or 11.0) [or 'r' to re-click, 's' to skip]: ").strip()

                    if user_val.lower() == 'r':
                        self.current_points = []
                        cv2.destroyWindow("LCD Flat Preview (Check Orientation)")
                        continue
                    elif user_val.lower() == 's' or user_val == '':
                        print("  Skipped.")
                        cv2.destroyWindow("LCD Flat Preview (Check Orientation)")
                        break
                    else:
                        # Save cropped LCD image
                        crop_filename = f"{self.mode}_{t_key}.jpg"
                        crop_path = os.path.join(self.crops_dir, crop_filename)
                        cv2.imwrite(crop_path, warped)

                        # Save annotation entry
                        self.annotations[t_key] = {
                            "timestamp_s": int(t_sec),
                            "value": user_val,
                            "corners": self.current_points,
                            "crop_file": crop_filename
                        }
                        self._save_annotations()
                        cv2.destroyWindow("LCD Flat Preview (Check Orientation)")
                        break

        cap.release()
        cv2.destroyAllWindows()
        self._save_annotations()
        print("\n🎉 Annotation session complete! Labeled frames are ready for training.")


def main():
    parser = argparse.ArgumentParser(description="Interactive 4-Corner LCD Annotator")
    parser.add_argument("--mode", choices=["voltage", "current"], default="voltage", help="Video mode to label")
    parser.add_argument("--samples", type=int, default=25, help="Number of sample frames to label (default: 25)")
    args = parser.parse_args()

    input_dir = os.path.join(REPO_ROOT, "multimeter_extractor", "input_videos")
    if args.mode == "voltage":
        v_path = os.path.join(input_dir, "Voltage Readings .mp4")
    else:
        v_path = os.path.join(input_dir, "Current readings.mp4")

    labeler = InteractiveLabeler(video_path=v_path, mode=args.mode, num_samples=args.samples)
    labeler.run()


if __name__ == "__main__":
    main()
