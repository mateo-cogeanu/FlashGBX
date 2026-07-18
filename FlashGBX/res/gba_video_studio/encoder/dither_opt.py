#encoder/dither_opt.py

import numpy as np
from numba import jit

@jit(nopython=True, cache=True)
def floyd_steinberg_jit(img):
    h, w, c = img.shape
    
    for y in range(h):
        if y % 2 == 0:
            for x in range(w):
                for channel in range(c):
                    old_pixel = img[y, x, channel]
                    
                    new_pixel = np.float32((round(old_pixel) >> 3) << 3)
                    img[y, x, channel] = new_pixel
                    
                    quant_error = old_pixel - new_pixel
                    
                    if x + 1 < w:
                        img[y, x + 1, channel] += quant_error * 0.4375
                    if y + 1 < h:
                        if x > 0:
                            img[y + 1, x - 1, channel] += quant_error * 0.1875
                        img[y + 1, x, channel] += quant_error * 0.3125
                        if x + 1 < w:
                            img[y + 1, x + 1, channel] += quant_error * 0.0625
        else:
            for x in range(w - 1, -1, -1):
                for channel in range(c):
                    old_pixel = img[y, x, channel]
                    
                    new_pixel = np.float32((round(old_pixel) >> 3) << 3)
                    img[y, x, channel] = new_pixel
                    
                    quant_error = old_pixel - new_pixel
                    
                    if x - 1 >= 0:
                        img[y, x - 1, channel] += quant_error * 0.4375
                    if y + 1 < h:
                        if x + 1 < w:
                            img[y + 1, x + 1, channel] += quant_error * 0.1875
                        img[y + 1, x, channel] += quant_error * 0.3125
                        if x - 1 >= 0:
                            img[y + 1, x - 1, channel] += quant_error * 0.0625
                        
    return img

def apply_dither_optimized(image_bgr: np.ndarray) -> np.ndarray:
    img = image_bgr.astype(np.float32)
    img = floyd_steinberg_jit(img)
    img = np.clip(img, 0, 255).astype(np.uint8)
    return img
