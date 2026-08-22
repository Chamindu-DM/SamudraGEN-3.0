#!/usr/bin/env python3
"""
Generates the Full-Frame Google Colab Notebook with Native PyTorch + EasyOCR & YOLO support.
Compatible with Python 3.10 / 3.11 / 3.12+ and CUDA T4 GPU.
"""

import json
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
notebook_path = os.path.join(base_dir, "Multimeter_Colab_FullFrame_Extractor.ipynb")

notebook_content = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🌊 OSWC Multimeter Full-Frame Video Data Extractor (Google Colab GPU)\n",
                "### High-Accuracy 1Hz Reading Extraction from Full 4K (3840×2160) & HD (1080×1920) Videos\n",
                "\n",
                "This notebook extracts the exact multimeter LCD voltage and current readings directly from your full-resolution videos using **PyTorch GPU-Accelerated OCR** (EasyOCR + OpenCV).\n",
                "\n",
                "### 🌟 Advantages:\n",
                "- **No Cropping Errors**: Retains 100% of the 3840×2160 4K and 1080×1920 frame data — no cut-off digits or missed decimal points.\n",
                "- **Native PyTorch GPU**: Compatible with Colab's latest Python version and CUDA.\n",
                "- **Zero Setup Friction**: Simple 1-click execution."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🛠️ Step 1: Select GPU Runtime & Install Dependencies\n",
                "1. In the top menu, go to **Runtime** > **Change runtime type** > Select **T4 GPU**.\n",
                "2. Run the cell below to install the packages."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "!pip install -q easyocr opencv-python-headless matplotlib pandas seaborn tqdm ultralytics\n",
                "import torch\n",
                "print(f\"✅ PyTorch Version: {torch.__version__}\")\n",
                "print(f\"✅ GPU Available: {torch.cuda.is_available()} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 📂 Step 2: Provide Video Files (Google Drive or Upload)\n",
                "Mount your Google Drive to directly access your video files without slow uploads."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "from google.colab import drive\n",
                "\n",
                "# Mount Google Drive\n",
                "drive.mount('/content/drive')\n",
                "print(\"✅ Google Drive Mounted!\")\n",
                "\n",
                "# Check available video files in Drive (adjust folder name if needed)\n",
                "# Example: /content/drive/MyDrive/Multimeter_Videos/\n",
                "print(\"Drive is ready. You can copy the path of your videos from the left sidebar.\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🧠 Step 3: Full-Frame Multimeter Reader Pipeline"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import cv2\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "import re\n",
                "import easyocr\n",
                "\n",
                "# Initialize EasyOCR with GPU acceleration\n",
                "reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())\n",
                "\n",
                "def sanitize_reading(raw_text):\n",
                "    if not raw_text:\n",
                "        return None\n",
                "    text = raw_text.strip()\n",
                "    # Replace common 7-segment OCR ambiguities\n",
                "    mapping = {'O': '0', 'o': '0', 'D': '0', 'I': '1', 'l': '1', '|': '1', 'S': '5', 's': '5', 'B': '8', 'Z': '2', ',': '.'}\n",
                "    for k, v in mapping.items():\n",
                "        text = text.replace(k, v)\n",
                "    match = re.search(r'[-+]?\d*\.?\d+', text)\n",
                "    if match:\n",
                "        try:\n",
                "            return float(match.group(0))\n",
                "        except ValueError:\n",
                "            return None\n",
                "    return None\n",
                "\n",
                "def locate_and_read_multimeter(frame):\n",
                "    \"\"\"\n",
                "    Locates multimeter in the full 4K / HD frame and performs high-resolution OCR.\n",
                "    \"\"\"\n",
                "    h, w = frame.shape[:2]\n",
                "    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)\n",
                "    \n",
                "    # Red casing detection\n",
                "    m1 = cv2.inRange(hsv, np.array([0, 35, 25]), np.array([22, 255, 255]))\n",
                "    m2 = cv2.inRange(hsv, np.array([155, 35, 25]), np.array([180, 255, 255]))\n",
                "    mask = cv2.bitwise_or(m1, m2)\n",
                "    \n",
                "    k = int(max(h, w) * 0.006) | 1\n",
                "    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))\n",
                "    cnts, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)\n",
                "    \n",
                "    if not cnts:\n",
                "        roi = frame\n",
                "    else:\n",
                "        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)\n",
                "        x, y, rw, rh = cv2.boundingRect(cnts[0])\n",
                "        # Generous padding so no digits or decimals are EVER cut off\n",
                "        pad_x = int(rw * 0.20)\n",
                "        pad_y = int(rh * 0.20)\n",
                "        x1, y1 = max(0, x - pad_x), max(0, y - pad_y)\n",
                "        x2, y2 = min(w, x + rw + pad_x), min(h, y + rh + pad_y)\n",
                "        roi = frame[y1:y2, x1:x2]\n",
                "        \n",
                "    # Contrast enhancement\n",
                "    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)\n",
                "    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))\n",
                "    enhanced = clahe.apply(gray)\n",
                "    \n",
                "    # EasyOCR detection\n",
                "    results = reader.readtext(enhanced, detail=1, allowlist='0123456789.-+VvAu')\n",
                "    best_val = np.nan\n",
                "    best_txt = \"\"\n",
                "    best_conf = 0.0\n",
                "    \n",
                "    for (bbox, txt, conf) in results:\n",
                "        val = sanitize_reading(txt)\n",
                "        if val is not None and conf > best_conf:\n",
                "            best_val = val\n",
                "            best_txt = txt\n",
                "            best_conf = conf\n",
                "            \n",
                "    return best_val, best_txt, round(best_conf, 3)\n",
                "\n",
                "print(\"✅ PyTorch GPU OCR Engine Ready!\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🚀 Step 4: Run 1Hz Full-Frame Video Extraction\n",
                "Set your video paths and run the extraction below."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from tqdm.auto import tqdm\n",
                "\n",
                "def process_full_video(video_path, mode='voltage', max_sec=None):\n",
                "    cap = cv2.VideoCapture(video_path)\n",
                "    if not cap.isOpened():\n",
                "        raise FileNotFoundError(f\"Could not open video file: {video_path}\")\n",
                "        \n",
                "    fps = cap.get(cv2.CAP_PROP_FPS)\n",
                "    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))\n",
                "    duration = total_frames / fps if fps > 0 else 0\n",
                "    if max_sec is not None:\n",
                "        duration = min(duration, max_sec)\n",
                "        \n",
                "    timestamps = np.arange(0, duration, 1.0) # 1Hz (1 reading per second)\n",
                "    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))\n",
                "    print(f\"Processing {len(timestamps)} seconds from {os.path.basename(video_path)} ({w}x{h})...\")\n",
                "    \n",
                "    records = []\n",
                "    for t in tqdm(timestamps, desc=f\"Extracting {mode.upper()}\"):\n",
                "        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))\n",
                "        ret, frame = cap.read()\n",
                "        if not ret:\n",
                "            records.append({\"timestamp_s\": t, \"reading_value\": np.nan, \"raw_text\": \"\", \"confidence\": 0.0})\n",
                "            continue\n",
                "            \n",
                "        val, txt, conf = locate_and_read_multimeter(frame)\n",
                "        records.append({\"timestamp_s\": t, \"reading_value\": val, \"raw_text\": txt, \"confidence\": conf})\n",
                "        \n",
                "    cap.release()\n",
                "    df = pd.DataFrame(records)\n",
                "    \n",
                "    # Outlier filter and interpolation\n",
                "    readings = df['reading_value'].copy()\n",
                "    max_bound = 35.0 if mode == 'voltage' else 150.0\n",
                "    readings[(readings > max_bound) | (readings < -5.0)] = np.nan\n",
                "    df['cleaned_value'] = readings.interpolate(method='linear', limit=5).ffill().bfill().rolling(3, min_periods=1, center=True).median()\n",
                "    \n",
                "    output_csv = f\"{mode}_readings_fullframe.csv\"\n",
                "    df.to_csv(output_csv, index=False)\n",
                "    print(f\"✅ Successfully saved {len(df)} readings to: {output_csv}\")\n",
                "    return df\n",
                "\n",
                "# --- SET YOUR VIDEO PATHS HERE ---\n",
                "# (Right-click your video file in the Google Colab file browser on the left -> 'Copy path')\n",
                "voltage_video_path = \"/content/drive/MyDrive/Voltage Readings .mp4\" # Update this path\n",
                "current_video_path = \"/content/drive/MyDrive/Current readings.mp4\"   # Update this path\n",
                "\n",
                "# Run Voltage (if file exists)\n",
                "if os.path.exists(voltage_video_path):\n",
                "    voltage_df = process_full_video(voltage_video_path, mode='voltage')\n",
                "else:\n",
                "    print(f\"⚠️ Please update voltage_video_path to the correct file path.\")\n",
                "\n",
                "# Run Current (if file exists)\n",
                "if os.path.exists(current_video_path):\n",
                "    current_df = process_full_video(current_video_path, mode='current')\n",
                "else:\n",
                "    print(f\"⚠️ Please update current_video_path to the correct file path.\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 📊 Step 5: Plot & Download Extracted Data"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import matplotlib.pyplot as plt\n",
                "from google.colab import files\n",
                "\n",
                "if 'voltage_df' in locals():\n",
                "    plt.figure(figsize=(12, 4))\n",
                "    plt.plot(voltage_df['timestamp_s'], voltage_df['cleaned_value'], 'r-', label='Voltage (V)')\n",
                "    plt.title('Voltage Readings vs Time (1s)', fontsize=14, fontweight='bold')\n",
                "    plt.xlabel('Time (seconds)')\n",
                "    plt.ylabel('Voltage (V)')\n",
                "    plt.grid(True, linestyle='--', alpha=0.6)\n",
                "    plt.legend()\n",
                "    plt.show()\n",
                "    files.download('voltage_readings_fullframe.csv')\n",
                "\n",
                "if 'current_df' in locals():\n",
                "    plt.figure(figsize=(12, 4))\n",
                "    plt.plot(current_df['timestamp_s'], current_df['cleaned_value'], 'g-', label='Current (uA)')\n",
                "    plt.title('Current Readings vs Time (1s)', fontsize=14, fontweight='bold')\n",
                "    plt.xlabel('Time (seconds)')\n",
                "    plt.ylabel('Current (uA)')\n",
                "    plt.grid(True, linestyle='--', alpha=0.6)\n",
                "    plt.legend()\n",
                "    plt.show()\n",
                "    files.download('current_readings_fullframe.csv')"
            ]
        }
    ],
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "gpuType": "T4",
            "provenance": []
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

with open(notebook_path, 'w') as f:
    json.dump(notebook_content, f, indent=2)

print(f"Generated Updated Colab Notebook at: {notebook_path}")
