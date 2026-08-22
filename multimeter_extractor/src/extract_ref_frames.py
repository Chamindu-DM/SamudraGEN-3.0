import cv2
import numpy as np

# Load t=60s frame for Current readings (1080x1920)
cap_c = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Current readings.mp4")
fps_c = cap_c.get(cv2.CAP_PROP_FPS)
cap_c.set(cv2.CAP_PROP_POS_FRAMES, int(60 * fps_c))
ret_c, frame_c = cap_c.read()
cap_c.release()

if ret_c:
    # Save unresized t=60s frame
    cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/current_full_t60.jpg", frame_c)
    print("Saved current_full_t60.jpg with shape:", frame_c.shape)

# Load t=60s frame for Voltage readings (3840x2160)
cap_v = cv2.VideoCapture("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/input_videos/Voltage Readings .mp4")
fps_v = cap_v.get(cv2.CAP_PROP_FPS)
cap_v.set(cv2.CAP_PROP_POS_FRAMES, int(60 * fps_v))
ret_v, frame_v = cap_v.read()
cap_v.release()

if ret_v:
    cv2.imwrite("/Users/chamindu/Documents/GitHub/SamudraGEN-3.0/multimeter_extractor/debug_frames/time_survey/voltage_full_t60.jpg", frame_v)
    print("Saved voltage_full_t60.jpg with shape:", frame_v.shape)
