#encoder/gop_processor.py

import numpy as np
from core_encoder import (
    classify_4x4_blocks_unified, generate_unified_codebook, 
    identify_updated_big_blocks, DEFAULT_UNIFIED_CODEBOOK_SIZE, 
    BYTES_PER_BLOCK, calculate_2x2_block_variance
)

def extract_effective_blocks_from_big_blocks(blocks: np.ndarray, big_block_positions: set,
                                           variance_threshold: float = 5.0) -> list:
    blocks_h, blocks_w = blocks.shape[:2]
    effective_blocks = []
    
    for big_by, big_bx in big_block_positions:
        blocks_4x4 = []
        for sub_by in range(2):
            for sub_bx in range(2):
                by = big_by * 2 + sub_by
                bx = big_bx * 2 + sub_bx
                if by < blocks_h and bx < blocks_w:
                    blocks_4x4.append(blocks[by, bx])
                else:
                    blocks_4x4.append(np.zeros(BYTES_PER_BLOCK, dtype=np.uint8))
        
        all_2x2_blocks_are_uniform = True
        for block in blocks_4x4:
            if calculate_2x2_block_variance(block) > variance_threshold:
                all_2x2_blocks_are_uniform = False
                break
        
        if all_2x2_blocks_are_uniform:
            downsampled_block = np.zeros(BYTES_PER_BLOCK, dtype=np.uint8)
            
            y_values = []
            cb_values = []
            cr_values = []
            
            for block in blocks_4x4:
                avg_y = np.mean(block[:4])
                y_values.append(int(avg_y))
                
                avg_cb = np.mean(block[4:8])
                avg_cr = np.mean(block[8:12])
                cb_values.append(avg_cb)
                cr_values.append(avg_cr)
            
            downsampled_block[:4] = np.array(y_values, dtype=np.uint8)
            
            avg_cb_final = np.clip(np.mean(cb_values), 0, 255).astype(np.uint8)
            avg_cr_final = np.clip(np.mean(cr_values), 0, 255).astype(np.uint8)
            
            for i in range(4):
                downsampled_block[4 + i] = avg_cb_final
                downsampled_block[8 + i] = avg_cr_final
            
            effective_blocks.extend([downsampled_block] * 4)
        else:
            effective_blocks.extend(blocks_4x4)
    
    return effective_blocks

def process_single_gop_frame(args_tuple):
    (gop_start, gop_end, frame_data_list, variance_threshold,
     diff_threshold, codebook_size, kmeans_max_iter, i_frame_weight) = args_tuple

    try:
        if isinstance(frame_data_list, tuple) and len(frame_data_list) == 5:
            mmap_path, shape, dtype, slice_start, slice_end = frame_data_list
            import numpy as _np
            _mmap = _np.memmap(mmap_path, dtype=dtype, mode='r', shape=shape)
            frame_data_list = [_mmap[i].copy() for i in range(slice_start, slice_end)]
            del _mmap

        effective_blocks = []
        block_types_list = []

        prev_blocks = None

        for frame_idx in range(gop_start, gop_end):
            relative_frame_idx = frame_idx - gop_start
            if relative_frame_idx >= len(frame_data_list):
                break

            frame_blocks = frame_data_list[relative_frame_idx]
            if frame_blocks.size == 0:
                continue
            
            is_i_frame = (frame_idx == gop_start)
            
            if is_i_frame:
                blocks_h, blocks_w = frame_blocks.shape[:2]
                big_blocks_h = blocks_h // 2
                big_blocks_w = blocks_w // 2
                updated_big_blocks = {(big_by, big_bx) for big_by in range(big_blocks_h) for big_bx in range(big_blocks_w)}
            else:
                updated_big_blocks = identify_updated_big_blocks(frame_blocks, prev_blocks, diff_threshold)
            
            frame_effective_blocks = extract_effective_blocks_from_big_blocks(
                frame_blocks, updated_big_blocks, variance_threshold)
            
            if is_i_frame:
                weighted_blocks = frame_effective_blocks * i_frame_weight
                effective_blocks.extend(weighted_blocks)
            else:
                effective_blocks.extend(frame_effective_blocks)
            
            frame_blocks_list, block_types = classify_4x4_blocks_unified(frame_blocks, variance_threshold)
            block_types_list.append((frame_idx, block_types))
            
            prev_blocks = frame_blocks.copy()
        
        unified_codebook = generate_unified_codebook(effective_blocks, codebook_size, kmeans_max_iter)
        
        return {
            'gop_start': gop_start,
            'unified_codebook': unified_codebook,
            'block_types_list': block_types_list,
            'total_blocks_count': len(effective_blocks),
            'success': True
        }
        
    except Exception as e:
        return {
            'gop_start': gop_start,
            'error': str(e),
            'success': False
        }

def _progress_bar(done, total, prefix="", width=30):
    pct = min(done / max(total, 1), 1.0)
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r  {prefix}[{bar}] {pct*100:5.1f}%  {done}/{total}", end="", flush=True)


def generate_gop_unified_codebooks(frames, i_frame_interval: int,
                                  variance_threshold: float, diff_threshold: float,
                                  codebook_size: int = DEFAULT_UNIFIED_CODEBOOK_SIZE,
                                  kmeans_max_iter: int = 100, i_frame_weight: int = 3,
                                  max_workers: int = None,
                                  tmp_dir: str = None) -> dict:
    import pickle, os

    if tmp_dir is None:
        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
    os.makedirs(tmp_dir, exist_ok=True)

    frames_is_mmap = hasattr(frames, 'filename')
    mmap_ref = None
    if frames_is_mmap:
        mmap_ref = (frames.filename, frames.shape, frames.dtype.str)

    i_frame_positions = [i for i in range(len(frames)) if i % i_frame_interval == 0]

    tasks = []
    for gop_idx, gop_start in enumerate(i_frame_positions):
        gop_end = i_frame_positions[gop_idx + 1] if gop_idx + 1 < len(i_frame_positions) else len(frames)
        if frames_is_mmap:
            frame_ref = (mmap_ref[0], mmap_ref[1], mmap_ref[2], gop_start, gop_end)
        else:
            frame_ref = list(frames[gop_start:gop_end])
        if gop_end > gop_start:
            tasks.append((gop_start, gop_end, frame_ref,
                          variance_threshold, diff_threshold, codebook_size,
                          kmeans_max_iter, i_frame_weight))

    total_tasks = len(tasks)
    print(f"Encoding GOP codebooks: {len(frames)} frames, {total_tasks} GOPs", flush=True)

    completed_tasks = 0
    gop_codebook_paths = {}

    for task in tasks:
        result = process_single_gop_frame(task)
        completed_tasks += 1
        _progress_bar(completed_tasks, total_tasks, prefix="GOP codebooks ")

        gop_start = result.get('gop_start', -1)
        if result['success']:
            pkl_path = os.path.join(tmp_dir, f"gop_{gop_start}.pkl")
            with open(pkl_path, 'wb') as f:
                pickle.dump({
                    'unified_codebook': result['unified_codebook'],
                    'block_types_list': result['block_types_list'],
                }, f, protocol=4)
            gop_codebook_paths[gop_start] = pkl_path
            del result
        else:
            print(f"\n  ❌ GOP {gop_start} failed: {result.get('error', 'unknown')}")
            gop_codebook_paths[gop_start] = None

    print()

    for gop_start in i_frame_positions:
        if gop_start not in gop_codebook_paths or gop_codebook_paths[gop_start] is None:
            print(f"  ⚠️  GOP {gop_start} missing, using default codebook")
            pkl_path = os.path.join(tmp_dir, f"gop_{gop_start}.pkl")
            default_codebook = np.zeros((codebook_size, BYTES_PER_BLOCK), dtype=np.uint8)
            with open(pkl_path, 'wb') as f:
                pickle.dump({'unified_codebook': default_codebook, 'block_types_list': []}, f, protocol=4)
            gop_codebook_paths[gop_start] = pkl_path

    print(f"  ✅ All {total_tasks} GOPs done — codebooks saved to temp/")
    return gop_codebook_paths