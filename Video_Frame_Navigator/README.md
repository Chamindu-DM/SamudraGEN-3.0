# SamudraGEN 3.0: Dual Video Frame Navigator & Slicer

A lightweight, standalone desktop GUI application to browse, inspect, and slice **Voltage** and **Current** measurement videos frame-by-frame (1 FPS or 2 FPS) with synchronized side-by-side display and time overlay banners.

Compatible with **macOS**, **Windows**, and **Linux**.

---

## 1. Quick Start (1-Click Run)

### On Windows:
Double-click `run_windows.bat` (or open Command Prompt and run `run_windows.bat`).

### On macOS / Linux:
Open Terminal in this folder and run:
```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```
Or directly with Python:
```bash
pip install -r requirements.txt
python3 app.py
```

---

## 2. How to Use the Application

1. **Select Videos**:
   - Click **Browse Voltage** to pick your Voltage video file (`.mp4`, `.avi`, `.mov`).
   - Click **Browse Current** to pick your Current video file (`.mp4`, `.avi`, `.mov`).
2. **Choose Sampling Rate**:
   - **1 Frame / Sec (1.0 Hz)**: Slices video into 1 frame for every 1 second ($t=0s, 1s, 2s, 3s...$).
   - **2 Frames / Sec (2.0 Hz)**: Slices video into 2 frames for every 1 second ($t=0.0s, 0.5s, 1.0s, 1.5s...$).
3. **Load Videos**:
   - Click the green **LOAD & SLICE VIDEOS** button.
4. **View Modes**:
   - **Side-by-Side**: Synchronized comparison of both Voltage and Current videos on the same screen.
   - **Voltage Only**: Fullscreen view of the Voltage video.
   - **Current Only**: Fullscreen view of the Current video.

---

## 3. Keyboard Shortcuts & Navigation

| Action | Keyboard Shortcut | On-Screen Control |
| :--- | :--- | :--- |
| **Previous Frame** | `Left Arrow (<-)` or `A` | `< Prev (Left)` button |
| **Next Frame** | `Right Arrow (->)` or `D` | `Next (Right) >` button |
| **Jump -10 Seconds** | `Down Arrow` or `S` | `<< -10s` button |
| **Jump +10 Seconds** | `Up Arrow` or `W` | `+10s >>` button |
| **Play / Pause** | `Spacebar` | `Play [Space]` button |
| **Jump to Start / End** | `Home` / `End` | `\|<< Start` / `End >>\|` |
| **Jump to Specific Second** | Type second & press `Enter` | `Jump to (s)` input field + `Go` |
| **Timeline Scrubbing** | Mouse drag | Timeline Slider Bar |

---

## 4. Exporting Frames

- **Save Current Frame**: Saves the currently displayed frame(s) with timestamp banner as an image (`.jpg`).
- **Export All Sliced Frames**: Automatically extracts all sliced frames across the entire video into `voltage_frames/` and `current_frames/` subfolders inside your selected directory.

---

## 5. System Requirements
- Python 3.8 or newer
- Dependencies: `opencv-python`, `pillow`, `numpy` (auto-installed by launcher scripts).
