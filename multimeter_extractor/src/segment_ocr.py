"""
7-Segment LCD Display OCR Engine
Refined for UNI-T UT33A+ digital multimeter.
"""

import cv2
import numpy as np


# 7-Segment Boolean Definition
# Segments: (A: top, B: top-right, C: bottom-right, D: bottom, E: bottom-left, F: top-left, G: middle)
DIGIT_PATTERNS = {
    (1, 1, 1, 1, 1, 1, 0): '0',
    (0, 1, 1, 0, 0, 0, 0): '1',
    (1, 1, 0, 1, 1, 0, 1): '2',
    (1, 1, 1, 1, 0, 0, 1): '3',
    (0, 1, 1, 0, 0, 1, 1): '4',
    (1, 0, 1, 1, 0, 1, 1): '5',
    (1, 0, 1, 1, 1, 1, 1): '6',
    (1, 1, 1, 0, 0, 0, 0): '7',
    (1, 1, 1, 1, 1, 1, 1): '8',
    (1, 1, 1, 1, 0, 1, 1): '9',
    (1, 1, 1, 0, 0, 1, 1): '9',  # Alternate 9 without bottom bar
    (0, 0, 0, 0, 0, 0, 1): '-',  # Minus sign
    (0, 0, 0, 0, 0, 0, 0): ' ',  # Blank
}


class SevenSegmentOCR:
    def __init__(self, segment_thresh=0.22):
        self.segment_thresh = segment_thresh

    def decode_single_digit(self, digit_binary):
        """
        Samples the 7 segments of a binarized single-digit image and returns the best matching character.
        """
        h, w = digit_binary.shape[:2]
        if h < 12 or w < 6:
            return ' ', 0.0

        # Segment sample regions accounting for 7-segment slant
        seg_boxes = {
            'A': (0.00, 0.16, 0.15, 0.85),
            'B': (0.12, 0.45, 0.70, 1.00),
            'C': (0.52, 0.85, 0.70, 1.00),
            'D': (0.84, 1.00, 0.15, 0.85),
            'E': (0.52, 0.85, 0.00, 0.30),
            'F': (0.12, 0.45, 0.00, 0.30),
            'G': (0.40, 0.58, 0.15, 0.85),
        }

        seg_scores = {}
        seg_bits = []

        for seg in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            y1_f, y2_f, x1_f, x2_f = seg_boxes[seg]
            y1, y2 = int(y1_f * h), int(y2_f * h)
            x1, x2 = int(x1_f * w), int(x2_f * w)
            roi = digit_binary[y1:y2, x1:x2]
            score = np.mean(roi > 128) if roi.size > 0 else 0.0
            seg_scores[seg] = score
            seg_bits.append(1 if score >= self.segment_thresh else 0)

        seg_tuple = tuple(seg_bits)

        # Exact match
        if seg_tuple in DIGIT_PATTERNS:
            char = DIGIT_PATTERNS[seg_tuple]
            conf = sum(score if bit == 1 else (1.0 - score) for bit, score in zip(seg_bits, seg_scores.values())) / 7.0
            return char, conf

        # Distance match
        best_char = '?'
        best_dist = 999
        best_conf = 0.0

        for pattern, char in DIGIT_PATTERNS.items():
            dist = sum(abs(a - b) for a, b in zip(seg_tuple, pattern))
            if dist < best_dist:
                best_dist = dist
                best_char = char
                conf = sum(score if bit == 1 else (1.0 - score) for bit, score in zip(pattern, seg_scores.values())) / 7.0
                best_conf = max(0.0, conf - (dist * 0.15))

        if best_dist <= 2:
            return best_char, best_conf
        return '?', 0.0

    def parse_lcd_readout(self, lcd_binary, num_digits=4):
        """
        Extracts and parses digits from the rectified LCD display.
        """
        h, w = lcd_binary.shape[:2]
        
        # Crop inner area to completely exclude top icon labels and bottom border
        y_top = int(h * 0.20)
        y_bot = int(h * 0.90)
        x_left = int(w * 0.18)
        x_right = int(w * 0.92)
        
        inner = lcd_binary[y_top:y_bot, x_left:x_right]
        ih, iw = inner.shape[:2]
        
        if ih < 10 or iw < 20:
            return "", 0.0

        # Slot width for 4 digits
        slot_w = iw / float(num_digits)
        
        chars = []
        confs = []
        dp_positions = []
        
        for i in range(num_digits):
            sx1 = int(i * slot_w)
            sx2 = int((i + 1) * slot_w)
            
            # Digit crop
            pad_x = int(slot_w * 0.08)
            digit_crop = inner[:, sx1 + pad_x : sx2 - pad_x]
            
            # Check if this slot contains active pixels
            if np.mean(digit_crop > 128) < 0.04:
                # Slot is completely empty
                continue
                
            char, conf = self.decode_single_digit(digit_crop)
            
            # Check for decimal point in bottom right of this slot
            dp_roi = inner[int(ih * 0.72) : ih, int(sx2 - slot_w * 0.28) : sx2]
            has_dp = (np.mean(dp_roi > 128) > 0.18) if dp_roi.size > 0 else False
            
            if char != ' ' and char != '?':
                chars.append(char)
                confs.append(conf)
                if has_dp and i < num_digits - 1:
                    dp_positions.append(len(chars))

        if not chars:
            return "", 0.0

        # Construct number string with AT MOST ONE decimal point
        res = ""
        # If any decimal point was detected, place only the most confident/first one
        best_dp = dp_positions[0] if dp_positions else None
        
        for idx, ch in enumerate(chars):
            res += ch
            if best_dp is not None and (idx + 1) == best_dp:
                res += "."

        # Remove invalid minus signs at the end
        if res.endswith('-'):
            res = res[:-1]

        avg_conf = np.mean(confs) if confs else 0.0
        return res, avg_conf
