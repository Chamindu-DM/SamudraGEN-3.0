# Multimeter Video 1Hz Data Extractor (OSWC Deployment Recovery)

This tool automatically extracts **1-second interval (1Hz)** voltage and current readings from multimeter videos recorded in low-light/nighttime ocean deployment conditions.

---

## Features
- **Accurate 1Hz Sampling**: Accurately samples frames at 1.0-second intervals (`timestamp = 1.0s, 2.0s, ...`).
- **Handheld Jitter & Perspective Rectification**: Tracks the UNI-T UT33A+ multimeter body and rectifies the LCD display into a flat, upright image.
- **Nighttime Lighting & Glare Filter**: Uses CLAHE contrast enhancement and adaptive binarization to isolate LCD 7-segment digits.
- **Dedicated 7-Segment Boolean Slot Decoder**: High precision OCR specifically tuned for digital multimeter LCDs with decimal point and minus sign detection.
- **Automated Data Export & Visualization**: Generates CSV files (`timestamp_s`, `reading_value`, `unit`, `confidence`) and time-series plots.

---

## Directory Structure
```
multimeter_extractor/
├── input_videos/            # Video files (Current readings.mp4, Voltage Readings .mp4)
├── output_data/             # Generated CSV files and plots
│   ├── current_readings.csv
│   ├── current_readings_plot.png
│   ├── voltage_readings.csv
│   └── voltage_readings_plot.png
├── debug_frames/            # Visual debug samples every 30 seconds
├── src/
│   ├── preprocessor.py      # CLAHE contrast, bilateral filtering, glare removal
│   ├── segment_ocr.py       # 7-segment boolean LCD digit parser
│   ├── lcd_tracker.py       # Multimeter detection and perspective warping
│   └── video_sampler.py     # Frame extraction loop and time-series post-processing
├── requirements.txt         # Dependencies
└── run_extractor.py         # Main execution script
```

---

## Usage

### 1. Run on Both Videos (Full Length)
```bash
python3 multimeter_extractor/run_extractor.py --mode all
```

### 2. Run on Voltage Video Only
```bash
python3 multimeter_extractor/run_extractor.py --mode voltage
```

### 3. Run on Current Video Only
```bash
python3 multimeter_extractor/run_extractor.py --mode current
```

### 4. Test on a 30-Second Clip First
```bash
python3 multimeter_extractor/run_extractor.py --mode voltage --start 60 --duration 30
```
