import cv2
import numpy as np
import os
import glob
import sys
sys.path.insert(0, "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0")

from multimeter_extractor.src.segment_ocr import SevenSegmentOCR
from multimeter_extractor.src.preprocessor import LCDPreprocessor

out_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/dataset_tests"
os.makedirs(out_dir, exist_ok=True)

# Test on 5 frames from Current and 5 frames from Voltage
sample_dir = "/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/sample_frames"
files = [
    "Current_readings_t0010s.jpg",
    "Current_readings_t0030s.jpg",
    "Current_readings_t0120s.jpg",
    "Current_readings_t0180s.jpg",
    "Current_readings_t0300s.jpg",
    "Voltage_Readings__t0010s.jpg",
    "Voltage_Readings__t0030s.jpg",
    "Voltage_Readings__t0120s.jpg",
    "Voltage_Readings__t0180s.jpg",
    "Voltage_Readings__t0300s.jpg"
]

print("Testing LCD detection on sample frames...")
