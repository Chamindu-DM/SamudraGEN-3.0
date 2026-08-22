#!/bin/bash
# =========================================================
# 1-Click Launcher for macOS & Linux
# =========================================================

echo "--------------------------------------------------------"
echo " Starting SamudraGEN Video Frame Navigator & Slicer GUI "
echo "--------------------------------------------------------"

# Check if Python is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python is not installed. Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Install dependencies if missing
echo "Checking dependencies (opencv-python, pillow, numpy)..."
$PYTHON_CMD -m pip install -q -r requirements.txt

# Run GUI
echo "Launching GUI..."
$PYTHON_CMD app.py
