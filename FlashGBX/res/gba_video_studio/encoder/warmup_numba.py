# encoder/warmup_numba.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

def run():
    import core_encoder as ce
    import dither_opt as do
    import motion_compensation as mc

    frame = np.zeros((160, 240, 3), dtype=np.uint8)
    block = np.zeros((80, 120, 12), dtype=np.uint8)
    single_block = np.zeros(12, dtype=np.uint8)
    y_vals = np.zeros(4, dtype=np.float64)
    flat = np.zeros((9600, 12), dtype=np.uint8)
    diffs = np.zeros((80, 120), dtype=np.float64)

    ce.pack_yuv444_frame(frame)
    ce.calculate_2x2_block_variance(single_block)
    ce.calculate_block_variance_numba(y_vals)
    ce.compute_2x2_block_differences_numba(flat, flat, 80, 120)
    ce.identify_updated_big_blocks(block, block, 2.5)
    ce.quantize_blocks_unified(flat[:4], flat[:4])
    ce.classify_4x4_blocks_unified(block, 10.0)

    do.apply_dither_optimized(frame.copy())

    encoded_mv = mc.encode_motion_vector(1, 1)
    mc.decode_motion_vector(encoded_mv)
    mc.get_8x8_block_zone_info(0)
    mc.calculate_mse_8x8_blocks(block, block, 0, 0, 0, 0)
    mc.count_updated_2x2_blocks_no_motion(block, block, 0, 0, 2.5)
    mc.calculate_2x2_block_difference_unified(single_block, single_block)


if __name__ == "__main__":
    run()
