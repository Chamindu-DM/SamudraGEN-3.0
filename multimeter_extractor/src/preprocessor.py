"""
Image preprocessing and enhancement module for multimeter LCD recognition under nighttime illumination.
"""

import cv2
import numpy as np


class LCDPreprocessor:
    def __init__(self, target_size=(320, 160)):
        self.target_size = target_size

    def rectify_lcd(self, image, corners):
        """
        Warps a quadrilateral LCD region defined by 4 corner points (top-left, top-right, bottom-right, bottom-left)
        into a standard flat upright rectangular image of size target_size (width, height).
        """
        tw, th = self.target_size
        dst_pts = np.array([
            [0, 0],
            [tw - 1, 0],
            [tw - 1, th - 1],
            [0, th - 1]
        ], dtype=np.float32)
        
        src_pts = np.array(corners, dtype=np.float32)
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (tw, th))
        return warped

    def enhance_contrast(self, image):
        """
        Enhances contrast using CLAHE and bilateral filtering to remove nighttime noise.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        # Bilateral filter to smooth noise while keeping segment edges crisp
        denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        return enhanced

    def suppress_glare(self, image):
        """
        Detects bright specular glare spots from flashlights and attenuates them.
        """
        if len(image.shape) == 3:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
        else:
            v_channel = image.copy()
            
        # Glare mask: extreme brightness
        _, glare_mask = cv2.threshold(v_channel, 240, 255, cv2.THRESH_BINARY)
        
        if cv2.countNonZero(glare_mask) > 0:
            # Dilate glare mask slightly
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            glare_mask = cv2.dilate(glare_mask, kernel)
            if len(image.shape) == 3:
                inpainted = cv2.inpaint(image, glare_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                return inpainted
        return image

    def binarize(self, enhanced_gray):
        """
        Produces clean binary image where dark LCD segments are WHITE (255) and background is BLACK (0).
        """
        # Adaptive Gaussian thresholding works very robustly with varying backlight
        binary_adapt = cv2.adaptiveThreshold(
            enhanced_gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=25,
            C=12
        )
        
        # Otsu thresholding as alternative/blend
        _, binary_otsu = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Combine (intersection to remove outer border noise, or adaptive as primary)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        clean_binary = cv2.morphologyEx(binary_adapt, cv2.MORPH_OPEN, kernel)
        
        return clean_binary
