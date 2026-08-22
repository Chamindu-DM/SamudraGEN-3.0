#!/usr/bin/env python3
"""
SamudraGEN 3.0: Dual Video Frame Navigator & Slicer (Standalone Edition)
Cross-Platform GUI (macOS & Windows Compatible)
"""

import os
import sys
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np


class CustomButton(tk.Frame):
    """
    Cross-platform high-contrast button that renders identically on macOS, Windows, and Linux.
    """
    def __init__(self, parent, text, command, bg_color="#3b3b4f", hover_color="#00adb5", 
                 fg_color="#ffffff", font=("Arial", 10, "bold"), padx=12, pady=6, width=None):
        super().__init__(parent, bg=bg_color, cursor="hand2", highlightthickness=1, highlightbackground="#555566")
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        
        self.label = tk.Label(self, text=text, bg=bg_color, fg=fg_color, font=font, padx=padx, pady=pady)
        if width is not None:
            self.label.configure(width=width)
        self.label.pack(fill=tk.BOTH, expand=True)
        
        self.bind("<Button-1>", lambda e: self._on_click())
        self.label.bind("<Button-1>", lambda e: self._on_click())
        
        self.bind("<Enter>", lambda e: self._on_enter())
        self.label.bind("<Enter>", lambda e: self._on_enter())
        
        self.bind("<Leave>", lambda e: self._on_leave())
        self.label.bind("<Leave>", lambda e: self._on_leave())

    def _on_click(self):
        if self.command:
            self.command()

    def _on_enter(self):
        self.configure(bg=self.hover_color, highlightbackground=self.hover_color)
        self.label.configure(bg=self.hover_color)

    def _on_leave(self):
        self.configure(bg=self.bg_color, highlightbackground="#555566")
        self.label.configure(bg=self.bg_color)

    def set_text(self, new_text):
        self.label.configure(text=new_text)

    def set_bg(self, new_bg):
        self.bg_color = new_bg
        self.configure(bg=new_bg)
        self.label.configure(bg=new_bg)


class VideoFrameNavigatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SamudraGEN - Video Frame Navigator & Slicer")
        self.root.geometry("1380x880")
        self.root.minsize(1050, 680)

        self.bg_color = "#181820"
        self.panel_color = "#252530"
        self.accent_color = "#00adb5"
        self.text_color = "#ffffff"
        
        self.root.configure(bg=self.bg_color)
        
        # State variables
        self.voltage_path = tk.StringVar(value="")
        self.current_path = tk.StringVar(value="")
        self.fps_mode = tk.DoubleVar(value=1.0) # 1.0 = 1 fps, 2.0 = 2 fps
        self.view_mode = tk.StringVar(value="Side-by-Side")
        
        self.cap_v = None
        self.cap_c = None
        self.fps_v = 0.0
        self.fps_c = 0.0
        self.total_frames_v = 0
        self.total_frames_c = 0
        self.duration_s = 0.0
        
        self.timestamps = []
        self.current_idx = 0
        self.is_playing = False
        self.play_job = None
        
        self._build_ui()
        self._bind_keys()

    def _build_ui(self):
        # 1. Top Control Panel
        top_frame = tk.Frame(self.root, bg=self.panel_color, padx=14, pady=12, highlightthickness=1, highlightbackground="#3a3a4c")
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(12, 6))

        # Row 1: Voltage Video
        row1 = tk.Frame(top_frame, bg=self.panel_color)
        row1.pack(fill=tk.X, pady=3)
        
        tk.Label(row1, text="Voltage Video:", fg="#00ffcc", bg=self.panel_color, font=("Arial", 10, "bold"), width=14, anchor="w").pack(side=tk.LEFT)
        v_entry = tk.Entry(row1, textvariable=self.voltage_path, bg="#121218", fg="#ffffff", insertbackground="white", font=("Arial", 10))
        v_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        CustomButton(row1, text="Browse Voltage", command=self._browse_voltage, bg_color="#3a3a4c", hover_color="#00adb5", padx=10, pady=4).pack(side=tk.LEFT)

        # Row 2: Current Video
        row2 = tk.Frame(top_frame, bg=self.panel_color)
        row2.pack(fill=tk.X, pady=3)
        
        tk.Label(row2, text="Current Video:", fg="#ffb703", bg=self.panel_color, font=("Arial", 10, "bold"), width=14, anchor="w").pack(side=tk.LEFT)
        c_entry = tk.Entry(row2, textvariable=self.current_path, bg="#121218", fg="#ffffff", insertbackground="white", font=("Arial", 10))
        c_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        CustomButton(row2, text="Browse Current", command=self._browse_current, bg_color="#3a3a4c", hover_color="#ffb703", padx=10, pady=4).pack(side=tk.LEFT)

        # Row 3: Settings & Load
        row3 = tk.Frame(top_frame, bg=self.panel_color)
        row3.pack(fill=tk.X, pady=(8, 2))

        tk.Label(row3, text="Sampling Rate:", fg="#ffffff", bg=self.panel_color, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        
        rb1 = tk.Radiobutton(row3, text="1 Frame / Sec (1.0 Hz)", variable=self.fps_mode, value=1.0, 
                             bg=self.panel_color, fg="#ffffff", selectcolor="#121218", activebackground=self.panel_color, 
                             activeforeground="#00ffcc", font=("Arial", 9, "bold"))
        rb1.pack(side=tk.LEFT, padx=6)
        
        rb2 = tk.Radiobutton(row3, text="2 Frames / Sec (2.0 Hz)", variable=self.fps_mode, value=2.0, 
                             bg=self.panel_color, fg="#ffffff", selectcolor="#121218", activebackground=self.panel_color, 
                             activeforeground="#00ffcc", font=("Arial", 9, "bold"))
        rb2.pack(side=tk.LEFT, padx=6)

        tk.Label(row3, text="  |  View:", fg="#ffffff", bg=self.panel_color, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(10, 4))
        view_dropdown = ttk.Combobox(row3, textvariable=self.view_mode, values=["Side-by-Side", "Voltage Only", "Current Only"], state="readonly", width=14)
        view_dropdown.pack(side=tk.LEFT, padx=4)
        view_dropdown.bind("<<ComboboxSelected>>", lambda e: self._render_current_frame())

        CustomButton(row3, text="LOAD & SLICE VIDEOS", command=self._load_videos, bg_color="#00adb5", hover_color="#00fff0", fg_color="#000000", font=("Arial", 10, "bold"), padx=16, pady=6).pack(side=tk.RIGHT, padx=4)

        # 2. Main Frame Display Canvas
        display_frame = tk.Frame(self.root, bg="#0d0d12", highlightthickness=1, highlightbackground="#333344")
        display_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        
        self.image_canvas = tk.Label(display_frame, bg="#0d0d12", text="Please select video files above and click 'LOAD & SLICE VIDEOS'", fg="#777788", font=("Arial", 13, "bold"))
        self.image_canvas.pack(fill=tk.BOTH, expand=True)

        # 3. Bottom Navigation & Slider Panel
        bottom_frame = tk.Frame(self.root, bg=self.panel_color, padx=14, pady=10, highlightthickness=1, highlightbackground="#3a3a4c")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(6, 12))

        # Slider Row
        slider_row = tk.Frame(bottom_frame, bg=self.panel_color)
        slider_row.pack(fill=tk.X, pady=(0, 8))

        self.slider = tk.Scale(slider_row, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False,
                              bg="#181820", fg="white", troughcolor="#3a3a4c", activebackground="#00adb5",
                              highlightthickness=0, command=self._on_slider_change)
        self.slider.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=4)

        # Navigation Controls Row
        nav_row = tk.Frame(bottom_frame, bg=self.panel_color)
        nav_row.pack(fill=tk.X)

        CustomButton(nav_row, text="|<< Start", command=self._go_start, bg_color="#3a3a4c", hover_color="#555566", padx=8, pady=5).pack(side=tk.LEFT, padx=3)
        CustomButton(nav_row, text="<< -10s", command=lambda: self._jump_seconds(-10), bg_color="#3a3a4c", hover_color="#555566", padx=8, pady=5).pack(side=tk.LEFT, padx=3)
        CustomButton(nav_row, text="< Prev (Left)", command=self._prev_frame, bg_color="#3a3a4c", hover_color="#555566", padx=10, pady=5).pack(side=tk.LEFT, padx=3)
        
        self.play_btn = CustomButton(nav_row, text="Play [Space]", command=self._toggle_play, bg_color="#00adb5", hover_color="#00fff0", fg_color="#000000", padx=14, pady=5)
        self.play_btn.pack(side=tk.LEFT, padx=4)

        CustomButton(nav_row, text="Next (Right) >", command=self._next_frame, bg_color="#3a3a4c", hover_color="#555566", padx=10, pady=5).pack(side=tk.LEFT, padx=3)
        CustomButton(nav_row, text="+10s >>", command=lambda: self._jump_seconds(10), bg_color="#3a3a4c", hover_color="#555566", padx=8, pady=5).pack(side=tk.LEFT, padx=3)
        CustomButton(nav_row, text="End >>|", command=self._go_end, bg_color="#3a3a4c", hover_color="#555566", padx=8, pady=5).pack(side=tk.LEFT, padx=3)

        # Jump to Time
        tk.Label(nav_row, text="  Jump to (s):", fg="#ffffff", bg=self.panel_color, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(10, 3))
        self.jump_entry = tk.Entry(nav_row, width=8, bg="#121218", fg="#ffffff", insertbackground="white", font=("Arial", 9))
        self.jump_entry.pack(side=tk.LEFT, padx=3)
        self.jump_entry.bind("<Return>", lambda e: self._on_jump_submit())
        CustomButton(nav_row, text="Go", command=self._on_jump_submit, bg_color="#3a3a4c", hover_color="#00adb5", padx=8, pady=4).pack(side=tk.LEFT, padx=2)

        # Export Action Buttons
        CustomButton(nav_row, text="Save Current Frame", command=self._save_current_snapshot, bg_color="#4f5d75", hover_color="#637089", padx=10, pady=5).pack(side=tk.RIGHT, padx=4)
        CustomButton(nav_row, text="Export All Sliced Frames", command=self._export_all_frames, bg_color="#2d6a4f", hover_color="#40916c", padx=12, pady=5).pack(side=tk.RIGHT, padx=4)

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self._prev_frame())
        self.root.bind("<Right>", lambda e: self._next_frame())
        self.root.bind("<Up>", lambda e: self._jump_seconds(10))
        self.root.bind("<Down>", lambda e: self._jump_seconds(-10))
        self.root.bind("<space>", lambda e: self._toggle_play())
        self.root.bind("<a>", lambda e: self._prev_frame())
        self.root.bind("<d>", lambda e: self._next_frame())
        self.root.bind("<w>", lambda e: self._jump_seconds(10))
        self.root.bind("<s>", lambda e: self._jump_seconds(-10))

    def _browse_voltage(self):
        f = filedialog.askopenfilename(title="Select Voltage Video File", filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")])
        if f:
            self.voltage_path.set(f)

    def _browse_current(self):
        f = filedialog.askopenfilename(title="Select Current Video File", filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")])
        if f:
            self.current_path.set(f)

    def _load_videos(self):
        v_p = self.voltage_path.get().strip()
        c_p = self.current_path.get().strip()
        
        if not v_p and not c_p:
            messagebox.showerror("Error", "Please select at least one video file (Voltage or Current)!")
            return

        if self.cap_v is not None:
            self.cap_v.release()
        if self.cap_c is not None:
            self.cap_c.release()
            
        durations = []
        if v_p and os.path.exists(v_p):
            self.cap_v = cv2.VideoCapture(v_p)
            self.fps_v = self.cap_v.get(cv2.CAP_PROP_FPS)
            self.total_frames_v = int(self.cap_v.get(cv2.CAP_PROP_FRAME_COUNT))
            dur_v = self.total_frames_v / self.fps_v if self.fps_v > 0 else 0
            durations.append(dur_v)
        else:
            self.cap_v = None

        if c_p and os.path.exists(c_p):
            self.cap_c = cv2.VideoCapture(c_p)
            self.fps_c = self.cap_c.get(cv2.CAP_PROP_FPS)
            self.total_frames_c = int(self.cap_c.get(cv2.CAP_PROP_FRAME_COUNT))
            dur_c = self.total_frames_c / self.fps_c if self.fps_c > 0 else 0
            durations.append(dur_c)
        else:
            self.cap_c = None

        if not durations:
            messagebox.showerror("Error", "Could not open any of the specified video files.")
            return

        self.duration_s = max(durations)
        step = 1.0 / self.fps_mode.get()
        self.timestamps = list(np.arange(0, self.duration_s + 0.001, step))
        
        self.slider.configure(from_=0, to=len(self.timestamps) - 1)
        self.current_idx = 0
        self.slider.set(0)
        
        self._render_current_frame()
        messagebox.showinfo("Success", f"Indexed {len(self.timestamps)} frames ({self.duration_s:.1f}s duration at {self.fps_mode.get():.0f} FPS sampling)!")

    def _render_current_frame(self):
        if not self.timestamps:
            return
            
        t_sec = self.timestamps[self.current_idx]
        v_img = None
        c_img = None
        
        if self.cap_v is not None:
            f_idx = int(t_sec * self.fps_v)
            self.cap_v.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = self.cap_v.read()
            if ret:
                v_img = frame

        if self.cap_c is not None:
            f_idx = int(t_sec * self.fps_c)
            self.cap_c.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = self.cap_c.read()
            if ret:
                c_img = frame

        mode = self.view_mode.get()
        composite = None
        
        if mode == "Voltage Only" or (v_img is not None and c_img is None):
            composite = self._annotate_frame(v_img, t_sec, "VOLTAGE READINGS", "#00ffcc")
        elif mode == "Current Only" or (c_img is not None and v_img is None):
            composite = self._annotate_frame(c_img, t_sec, "CURRENT READINGS", "#ffb703")
        else:
            ann_v = self._annotate_frame(v_img, t_sec, "VOLTAGE", "#00ffcc")
            ann_c = self._annotate_frame(c_img, t_sec, "CURRENT", "#ffb703")
            
            if ann_v is not None and ann_c is not None:
                h = min(ann_v.shape[0], ann_c.shape[0])
                w_v = int(ann_v.shape[1] * (h / ann_v.shape[0]))
                w_c = int(ann_c.shape[1] * (h / ann_c.shape[0]))
                resized_v = cv2.resize(ann_v, (w_v, h))
                resized_c = cv2.resize(ann_c, (w_c, h))
                
                sep = np.zeros((h, 8, 3), dtype=np.uint8) + 80
                composite = np.hstack([resized_v, sep, resized_c])
            elif ann_v is not None:
                composite = ann_v
            elif ann_c is not None:
                composite = ann_c

        if composite is None:
            return

        canvas_w = max(400, self.image_canvas.winfo_width())
        canvas_h = max(300, self.image_canvas.winfo_height())
        
        img_h, img_w = composite.shape[:2]
        scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        disp_w = max(1, int(img_w * scale))
        disp_h = max(1, int(img_h * scale))
        
        disp_img = cv2.resize(composite, (disp_w, disp_h))
        disp_rgb = cv2.cvtColor(disp_img, cv2.COLOR_BGR2RGB)
        
        pil_img = Image.fromarray(disp_rgb)
        tk_img = ImageTk.PhotoImage(image=pil_img)
        
        self.image_canvas.configure(image=tk_img, text="")
        self.image_canvas.image = tk_img

    def _annotate_frame(self, frame, t_sec, label, color_hex):
        if frame is None:
            ph = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(ph, f"No Signal: {label}", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (150, 150, 150), 2)
            return ph

        annotated = frame.copy()
        h, w = annotated.shape[:2]
        
        banner_h = int(max(50, h * 0.07))
        cv2.rectangle(annotated, (0, 0), (w, banner_h), (18, 18, 22), -1)
        
        b_color = (0, 255, 204) if "VOLT" in label else (3, 183, 255)
        cv2.rectangle(annotated, (0, banner_h - 4), (w, banner_h), b_color, -1)
        
        min_sec = f"{int(t_sec)//60:02d}:{t_sec%60:04.1f}"
        info_txt = f"[{label}]  Time: {t_sec:.1f}s ({min_sec})  |  Frame: {self.current_idx + 1} / {len(self.timestamps)}"
        
        font_scale = max(0.6, w / 1600.0)
        thickness = max(1, int(font_scale * 2.2))
        cv2.putText(annotated, info_txt, (20, int(banner_h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
        
        return annotated

    def _on_slider_change(self, val):
        idx = int(val)
        if 0 <= idx < len(self.timestamps):
            self.current_idx = idx
            self._render_current_frame()

    def _prev_frame(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.slider.set(self.current_idx)
            self._render_current_frame()

    def _next_frame(self):
        if self.current_idx < len(self.timestamps) - 1:
            self.current_idx += 1
            self.slider.set(self.current_idx)
            self._render_current_frame()

    def _jump_seconds(self, sec_offset):
        if not self.timestamps:
            return
        target_t = self.timestamps[self.current_idx] + sec_offset
        diffs = [abs(t - target_t) for t in self.timestamps]
        self.current_idx = int(np.argmin(diffs))
        self.slider.set(self.current_idx)
        self._render_current_frame()

    def _go_start(self):
        if self.timestamps:
            self.current_idx = 0
            self.slider.set(0)
            self._render_current_frame()

    def _go_end(self):
        if self.timestamps:
            self.current_idx = len(self.timestamps) - 1
            self.slider.set(self.current_idx)
            self._render_current_frame()

    def _on_jump_submit(self):
        txt = self.jump_entry.get().strip()
        if not txt or not self.timestamps:
            return
        try:
            val = float(txt)
            diffs = [abs(t - val) for t in self.timestamps]
            self.current_idx = int(np.argmin(diffs))
            self.slider.set(self.current_idx)
            self._render_current_frame()
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number in seconds (e.g. 133 or 120.5).")

    def _toggle_play(self):
        if not self.timestamps:
            return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.set_text("Pause [Space]")
            self.play_btn.set_bg("#ffb703")
            self._play_loop()
        else:
            self.play_btn.set_text("Play [Space]")
            self.play_btn.set_bg("#00adb5")
            if self.play_job is not None:
                self.root.after_cancel(self.play_job)
                self.play_job = None

    def _play_loop(self):
        if not self.is_playing:
            return
        if self.current_idx < len(self.timestamps) - 1:
            self.current_idx += 1
            self.slider.set(self.current_idx)
            self._render_current_frame()
            delay_ms = int(1000 / self.fps_mode.get())
            self.play_job = self.root.after(delay_ms, self._play_loop)
        else:
            self._toggle_play()

    def _save_current_snapshot(self):
        if not self.timestamps:
            return
        t_sec = self.timestamps[self.current_idx]
        out_dir = filedialog.askdirectory(title="Select Folder to Save Snapshot")
        if not out_dir:
            return
        
        saved = []
        if self.cap_v is not None:
            f_idx = int(t_sec * self.fps_v)
            self.cap_v.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = self.cap_v.read()
            if ret:
                p = os.path.join(out_dir, f"voltage_sec_{t_sec:05.1f}s.jpg")
                ann = self._annotate_frame(frame, t_sec, "VOLTAGE", "#00ffcc")
                cv2.imwrite(p, ann)
                saved.append(p)

        if self.cap_c is not None:
            f_idx = int(t_sec * self.fps_c)
            self.cap_c.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = self.cap_c.read()
            if ret:
                p = os.path.join(out_dir, f"current_sec_{t_sec:05.1f}s.jpg")
                ann = self._annotate_frame(frame, t_sec, "CURRENT", "#ffb703")
                cv2.imwrite(p, ann)
                saved.append(p)

        messagebox.showinfo("Saved", f"Saved {len(saved)} snapshot(s) to:\n{out_dir}")

    def _export_all_frames(self):
        if not self.timestamps:
            messagebox.showerror("Error", "Please load videos first!")
            return
            
        out_dir = filedialog.askdirectory(title="Select Destination Folder for Sliced Frames")
        if not out_dir:
            return
            
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Exporting Sliced Frames...")
        prog_win.geometry("450x160")
        prog_win.configure(bg=self.panel_color)
        prog_win.transient(self.root)
        prog_win.grab_set()

        lbl = tk.Label(prog_win, text="Exporting frames...", fg="white", bg=self.panel_color, font=("Arial", 11))
        lbl.pack(pady=(16, 8))
        
        prog_bar = ttk.Progressbar(prog_win, maximum=len(self.timestamps), length=380)
        prog_bar.pack(pady=8)
        
        v_folder = os.path.join(out_dir, "voltage_frames")
        c_folder = os.path.join(out_dir, "current_frames")
        if self.cap_v is not None:
            os.makedirs(v_folder, exist_ok=True)
        if self.cap_c is not None:
            os.makedirs(c_folder, exist_ok=True)

        for i, t_sec in enumerate(self.timestamps):
            if self.cap_v is not None:
                f_idx = int(t_sec * self.fps_v)
                self.cap_v.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = self.cap_v.read()
                if ret:
                    ann = self._annotate_frame(frame, t_sec, "VOLTAGE", "#00ffcc")
                    cv2.imwrite(os.path.join(v_folder, f"voltage_t_{t_sec:06.1f}s.jpg"), ann)

            if self.cap_c is not None:
                f_idx = int(t_sec * self.fps_c)
                self.cap_c.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = self.cap_c.read()
                if ret:
                    ann = self._annotate_frame(frame, t_sec, "CURRENT", "#ffb703")
                    cv2.imwrite(os.path.join(c_folder, f"current_t_{t_sec:06.1f}s.jpg"), ann)

            prog_bar['value'] = i + 1
            lbl.configure(text=f"Exporting frame {i+1} / {len(self.timestamps)} ({t_sec:.1f}s)...")
            prog_win.update()

        prog_win.destroy()
        messagebox.showinfo("Export Complete", f"Exported {len(self.timestamps)} sliced frames to:\n{out_dir}")


def main():
    root = tk.Tk()
    app = VideoFrameNavigatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
