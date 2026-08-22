#!/usr/bin/env python3
"""
Multimeter Video 1Hz Data Extractor
Extracts voltage and current readings from video files at 1-second intervals.
"""

import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Add repo root to python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from multimeter_extractor.src.video_sampler import VideoMultimeterExtractor


def plot_readings(csv_path, output_png_path, title, ylabel, ylim=None):
    df = pd.read_csv(csv_path)
    if 'timestamp_s' not in df.columns or 'reading_value' not in df.columns:
        return
        
    plt.figure(figsize=(12, 5))
    plt.plot(df['timestamp_s'], df['reading_value'], 'b.', alpha=0.4, label='Raw Reading')
    if 'interpolated_value' in df.columns:
        plt.plot(df['timestamp_s'], df['interpolated_value'], 'r-', linewidth=1.8, label='Cleaned & Filtered (1s)')
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    if ylim:
        plt.ylim(ylim)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_png_path, dpi=150)
    plt.close()
    print(f"Saved plot: {output_png_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract 1Hz multimeter readings from video.")
    parser.add_argument("--mode", choices=["all", "voltage", "current"], default="all",
                        help="Which video(s) to process")
    parser.add_argument("--duration", type=int, default=None,
                        help="Maximum duration in seconds to process (default: full video)")
    parser.add_argument("--start", type=int, default=0,
                        help="Start timestamp in seconds (default: 0)")
    args = parser.parse_args()

    base_dir = os.path.join(REPO_ROOT, "multimeter_extractor")
    input_dir = os.path.join(base_dir, "input_videos")
    output_dir = os.path.join(base_dir, "output_data")
    debug_dir = os.path.join(base_dir, "debug_frames")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(debug_dir, exist_ok=True)

    tasks = []
    if args.mode in ["all", "voltage"]:
        tasks.append({
            "mode": "voltage",
            "video": os.path.join(input_dir, "Voltage Readings .mp4"),
            "csv": os.path.join(output_dir, "voltage_readings.csv"),
            "plot": os.path.join(output_dir, "voltage_readings_plot.png"),
            "title": "Voltage Readings over Time (1s Interval)",
            "ylabel": "Voltage (V)",
            "ylim": (-2, 35)
        })
        
    if args.mode in ["all", "current"]:
        tasks.append({
            "mode": "current",
            "video": os.path.join(input_dir, "Current readings.mp4"),
            "csv": os.path.join(output_dir, "current_readings.csv"),
            "plot": os.path.join(output_dir, "current_readings_plot.png"),
            "title": "Current Readings over Time (1s Interval)",
            "ylabel": "Current (uA)",
            "ylim": (-2, 60)
        })

    for task in tasks:
        print("\n" + "="*70)
        print(f" STARTING EXTRACTION: {task['mode'].upper()} ")
        print(f" Input video: {task['video']}")
        print(f" Output CSV:  {task['csv']}")
        print("="*70)

        extractor = VideoMultimeterExtractor(
            mode=task["mode"],
            debug_dir=os.path.join(debug_dir, f"{task['mode']}_samples")
        )

        df = extractor.extract_from_video(
            video_path=task["video"],
            output_csv_path=task["csv"],
            sample_rate_hz=1.0,
            start_sec=args.start,
            max_duration_sec=args.duration
        )

        plot_readings(task["csv"], task["plot"], task["title"], task["ylabel"], ylim=task.get("ylim"))

    print("\n" + "="*70)
    print(" ALL EXTRACTION TASKS COMPLETED SUCCESSFULLY! ")
    print("="*70)


if __name__ == "__main__":
    main()
