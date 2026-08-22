@echo off
REM =========================================================
REM 1-Click Launcher for Windows
REM =========================================================

echo --------------------------------------------------------
echo  Starting SamudraGEN Video Frame Navigator ^& Slicer GUI
echo --------------------------------------------------------

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not found. Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo Checking dependencies (opencv-python, pillow, numpy)...
pip install -q -r requirements.txt

echo Launching GUI...
python app.py

pause
