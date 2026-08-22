import cv2
import numpy as np

def fix_multimeter_orientation(mm_img):
    """
    Ensures the multimeter is upright by checking that the LCD screen is in the upper half
    (the upper half has higher average luminance than the dark dial/socket area).
    """
    h, w = mm_img.shape[:2]
    top_half = cv2.cvtColor(mm_img[:int(h*0.4), :], cv2.COLOR_BGR2GRAY)
    bot_half = cv2.cvtColor(mm_img[int(h*0.6):, :], cv2.COLOR_BGR2GRAY)
    
    # If bottom half is brighter than top half, it's upside down -> rotate 180
    if np.mean(bot_half) > np.mean(top_half) + 15:
        return cv2.rotate(mm_img, cv2.ROTATE_180_CLOCKWISE)
    return mm_img
