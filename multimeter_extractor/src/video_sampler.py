"""
Video Sampler and Extraction Orchestrator
Extracts multimeter LCD readings at 1-second intervals from video files.
"""

import cv2
import numpy as np
import pandas as pd
import os
import sys
import time
from tqdm import tqdm

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor
from multimeter_extractor.src.lcd_tracker import MultimeterTracker


class VideoMultimeterExtractor:
    def __init__(self, mode='voltage', debug_dir=None):
        self.mode = mode.lower()
        self.ocr = SevenSegmentOCR(segment_thresh=0.22)
        self.preprocessor = LCDPreprocessor(target_size=(320, 160))
        self.tracker = MultimeterTracker(mode=self.mode)
        self.debug_dir = debug_dir
        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)

    def extract_from_video(self, video_path, output_csv_path, sample_rate_hz=1.0, start_sec=0, max_duration_sec=None):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        
        if max_duration_sec is not None:
            end_sec = min(duration_sec, start_sec + max_duration_sec)
        else:
            end_sec = duration_sec

        step_sec = 1.0 / sample_rate_hz
        timestamps = np.arange(start_sec, end_sec, step_sec)

        print(f"[{self.mode.upper()}] Processing {len(timestamps)} time steps (1s interval) from {video_path}...")
        
        results = []

        for t_sec in tqdm(timestamps, desc=f"Extracting {self.mode}"):
            frame_idx = int(t_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                results.append({
                    "timestamp_s": round(t_sec, 2),
                    "reading_value": np.nan,
                    "unit": "V" if self.mode == "voltage" else "uA",
                    "confidence": 0.0,
                    "status": "FRAME_READ_ERROR"
                })
                continue

            # Detect & extract LCD
            reading_str, conf, warped_lcd, status = self._process_single_frame(frame, t_sec)

            # Parse numeric value
            num_val = np.nan
            try:
                if reading_str:
                    num_val = float(reading_str)
            except Exception:
                num_val = np.nan

            unit_str = "V" if self.mode == "voltage" else "uA"

            results.append({
                "timestamp_s": round(t_sec, 2),
                "reading_value": num_val,
                "raw_text": reading_str,
                "unit": unit_str,
                "confidence": round(conf, 3),
                "status": status
            })

            # Save preview sample periodically (e.g. every 30 seconds)
            if int(t_sec) % 30 == 0 and warped_lcd is not None and self.debug_dir:
                sample_out = os.path.join(self.debug_dir, f"{self.mode}_sample_t{int(t_sec):04d}s.jpg")
                annotated = warped_lcd.copy()
                cv2.putText(annotated, f"t={int(t_sec)}s: {reading_str} {unit_str}", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imwrite(sample_out, annotated)

        cap.release()

        # Convert to DataFrame
        df = pd.DataFrame(results)
        df = self._clean_time_series(df)
        
        # Save CSV
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False)
        print(f"[{self.mode.upper()}] Extraction complete! Saved {len(df)} readings to {output_csv_path}")

        return df

    def _process_single_frame(self, frame, t_sec):
        rect, box = self.tracker.detect_multimeter(frame)
        if rect is None:
            return "", 0.0, None, "MULTIMETER_NOT_FOUND"

        lcd_crop, pts_orig = self.tracker.extract_lcd_roi(frame, rect, target_w=320, target_h=160)
        if lcd_crop is None or lcd_crop.size == 0:
            return "", 0.0, None, "LCD_CROP_EMPTY"

        # Preprocess LCD
        enhanced = self.preprocessor.enhance_contrast(lcd_crop)
        binary = self.preprocessor.binarize(enhanced)

        # Parse reading
        reading_str, conf = self.ocr.parse_lcd_readout(binary)
        
        status = "OK" if conf >= 0.20 and reading_str else "LOW_CONFIDENCE"
        return reading_str, conf, lcd_crop, status

    def _clean_time_series(self, df):
        cleaned = df.copy()
        readings = cleaned['reading_value'].copy()
        
        # Apply physical range filters for multimeter readings
        if self.mode == "voltage":
            # Realistic voltage range (0 - 30V)
            outlier_mask = (readings > 40.0) | (readings < -5.0)
            readings[outlier_mask] = np.nan
        else:
            # Realistic current range (0 - 100 uA)
            outlier_mask = (readings > 150.0) | (readings < -5.0)
            readings[outlier_mask] = np.nan

        # Linear interpolation for gaps up to 5 seconds
        interpolated = readings.interpolate(method='linear', limit=5).ffill().bfill()
        
        # Apply gentle rolling median filter (3-sample window) to remove single-second glitches
        cleaned['interpolated_value'] = interpolated.rolling(window=3, min_periods=1, center=True).median()
        
        return cleaned
