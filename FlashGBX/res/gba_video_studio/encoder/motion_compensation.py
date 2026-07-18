#encoder/motion_compensation.py

import numpy as np
from numba import jit, njit
from typing import List, Tuple, Dict
from collections import defaultdict

SCREEN_WIDTH = 240
SCREEN_HEIGHT = 160
BLOCK_8X8_SIZE = 8
BLOCK_2X2_SIZE = 2

BLOCKS_8X8_WIDTH = SCREEN_WIDTH // BLOCK_8X8_SIZE
BLOCKS_8X8_HEIGHT = SCREEN_HEIGHT // BLOCK_8X8_SIZE

BLOCKS_8X8_PER_ZONE_ROW = BLOCKS_8X8_WIDTH
BLOCKS_8X8_PER_ZONE_HEIGHT = 8
BLOCKS_8X8_PER_ZONE = BLOCKS_8X8_PER_ZONE_ROW * BLOCKS_8X8_PER_ZONE_HEIGHT
TOTAL_ZONES = (BLOCKS_8X8_HEIGHT + BLOCKS_8X8_PER_ZONE_HEIGHT - 1) // BLOCKS_8X8_PER_ZONE_HEIGHT

MOTION_RANGE = 7

DEFAULT_UPDATE_THRESHOLD = 6
DEFAULT_MIN_IMPROVEMENT_THRESHOLD = 2

@njit(cache=True)
def encode_motion_vector(dx: int, dy: int) -> int:
    return ((dy + MOTION_RANGE) << 4) | (dx + MOTION_RANGE)

@njit(cache=True)
def decode_motion_vector(encoded: int) -> Tuple[int, int]:
    dx = (encoded & 0x0F) - MOTION_RANGE
    dy = ((encoded >> 4) & 0x0F) - MOTION_RANGE
    return dx, dy

@njit(cache=True)
def get_8x8_block_zone_info(block_8x8_idx: int) -> Tuple[int, int]:
    block_row = block_8x8_idx // BLOCKS_8X8_WIDTH
    block_col = block_8x8_idx % BLOCKS_8X8_WIDTH
    
    zone_idx = block_row // BLOCKS_8X8_PER_ZONE_HEIGHT
    zone_relative_row = block_row % BLOCKS_8X8_PER_ZONE_HEIGHT
    zone_relative_idx = zone_relative_row * BLOCKS_8X8_PER_ZONE_ROW + block_col
    
    return zone_idx, zone_relative_idx

@njit(cache=True)
def calculate_mse_8x8_blocks(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                              cur_start_y: int, cur_start_x: int,
                              ref_start_y: int, ref_start_x: int) -> float:
    mse = 0.0
    blocks_h, blocks_w = current_blocks.shape[:2]
    
    for dy in range(4):
        for dx in range(4):
            cur_y = cur_start_y + dy
            cur_x = cur_start_x + dx
            ref_y = ref_start_y + dy
            ref_x = ref_start_x + dx
            
            if (cur_y >= blocks_h or cur_x >= blocks_w or
                ref_y >= blocks_h or ref_x >= blocks_w or
                ref_y < 0 or ref_x < 0):
                mse += 10000.0
                continue
            
            for i in range(4):
                cur_val = float(current_blocks[cur_y, cur_x, i])
                ref_val = float(prev_blocks[ref_y, ref_x, i])
                diff = cur_val - ref_val
                mse += diff * diff
    
    return mse / 16.0

@njit(cache=True)
def count_updated_2x2_blocks_after_motion(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                                          cur_start_y: int, cur_start_x: int,
                                          dx: int, dy: int, diff_threshold: float) -> int:
    updated_count = 0
    blocks_h, blocks_w = current_blocks.shape[:2]
    
    ref_start_y = cur_start_y + dy // 2
    ref_start_x = cur_start_x + dx // 2
    
    for dy_block in range(4):
        for dx_block in range(4):
            cur_y = cur_start_y + dy_block
            cur_x = cur_start_x + dx_block
            ref_y = ref_start_y + dy_block
            ref_x = ref_start_x + dx_block
            
            if (cur_y >= blocks_h or cur_x >= blocks_w or
                ref_y >= blocks_h or ref_x >= blocks_w or
                ref_y < 0 or ref_x < 0):
                updated_count += 1
                continue
            
            diff = calculate_2x2_block_difference_unified(
                current_blocks[cur_y, cur_x], prev_blocks[ref_y, ref_x]
            )
            
            if diff > diff_threshold:
                updated_count += 1
    
    return updated_count

@njit(cache=True)
def count_updated_2x2_blocks_no_motion(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                                        cur_start_y: int, cur_start_x: int,
                                        diff_threshold: float) -> int:
    updated_count = 0
    blocks_h, blocks_w = current_blocks.shape[:2]
    
    for dy_block in range(4):
        for dx_block in range(4):
            cur_y = cur_start_y + dy_block
            cur_x = cur_start_x + dx_block
            
            if cur_y >= blocks_h or cur_x >= blocks_w:
                updated_count += 1
                continue
            
            diff = calculate_2x2_block_difference_unified(
                current_blocks[cur_y, cur_x], prev_blocks[cur_y, cur_x]
            )
            
            if diff > diff_threshold:
                updated_count += 1
    
    return updated_count

@njit(cache=True)
def diamond_search_iteration(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                              cur_start_y: int, cur_start_x: int,
                              best_mv: Tuple[int, int], diamond_pattern: np.ndarray,
                              best_mse: float) -> Tuple[Tuple[int, int], float, bool]:
    current_best_mv = (0, 0)
    current_best_mse = best_mse
    have_update = False

    for i in range(diamond_pattern.shape[0]):
        dx = diamond_pattern[i, 0]
        dy = diamond_pattern[i, 1]
        new_dx = best_mv[0] + dx
        new_dy = best_mv[1] + dy

        if abs(new_dx) <= MOTION_RANGE and abs(new_dy) <= MOTION_RANGE:
            ref_start_y = cur_start_y + new_dy
            ref_start_x = cur_start_x + new_dx

            mse = calculate_mse_8x8_blocks(current_blocks, prev_blocks,
                                           cur_start_y, cur_start_x,
                                           ref_start_y, ref_start_x)

            if mse < current_best_mse:
                current_best_mse = mse
                current_best_mv = (new_dx, new_dy)
                have_update = True

    return current_best_mv, current_best_mse, have_update

def hierarchical_diamond_search(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                                 block_8x8_y: int, block_8x8_x: int,
                                 diff_threshold: float) -> Tuple[Tuple[int, int], float, int, int]:
    cur_start_y = block_8x8_y * 4
    cur_start_x = block_8x8_x * 4
    
    no_motion_updates = count_updated_2x2_blocks_no_motion(
        current_blocks, prev_blocks, cur_start_y, cur_start_x, diff_threshold
    )
    
    best_mv = (0, 0)
    best_mse = float('inf')

    large_diamond = np.array([(0,0), (0,4), (4,0), (0,-4), (-4,0), (2,2), (2,-2), (-2,2), (-2,-2)], dtype=np.int64)
    best_mv, best_mse, _ = diamond_search_iteration(current_blocks, prev_blocks,
                                                    cur_start_y, cur_start_x,
                                                    best_mv, large_diamond, best_mse)
    while True:
        new_mv, new_mse, have_update = diamond_search_iteration(current_blocks, prev_blocks,
                                                                cur_start_y, cur_start_x,
                                                                best_mv, large_diamond, best_mse)
        if not have_update:
            break
        best_mv, best_mse = new_mv, new_mse

    medium_diamond = np.array([(0,2), (2,0), (0,-2), (-2,0), (1,1), (1,-1), (-1,1), (-1,-1)], dtype=np.int64)
    while True:
        new_mv, new_mse, have_update = diamond_search_iteration(current_blocks, prev_blocks,
                                                                cur_start_y, cur_start_x,
                                                                best_mv, medium_diamond, best_mse)
        if not have_update:
            break
        best_mv, best_mse = new_mv, new_mse

    small_diamond = np.array([(0,1), (1,0), (0,-1), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)], dtype=np.int64)
    while True:
        new_mv, new_mse, have_update = diamond_search_iteration(current_blocks, prev_blocks,
                                                                cur_start_y, cur_start_x,
                                                                best_mv, small_diamond, best_mse)
        if not have_update:
            break
        best_mv, best_mse = new_mv, new_mse
    
    dx, dy = best_mv
    updates_needed = count_updated_2x2_blocks_after_motion(
        current_blocks, prev_blocks, cur_start_y, cur_start_x, dx, dy, diff_threshold
    )
    
    return best_mv, best_mse, updates_needed, no_motion_updates

def detect_motion_compensation_candidates(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                                          diff_threshold: float,
                                          update_threshold: int = DEFAULT_UPDATE_THRESHOLD,
                                          min_improvement_threshold: int = DEFAULT_MIN_IMPROVEMENT_THRESHOLD) -> Dict:
    motion_candidates = {}
    total_8x8_blocks = BLOCKS_8X8_WIDTH * BLOCKS_8X8_HEIGHT
    
    motion_rejected_count = 0
    early_skip_count = 0
    
    for block_8x8_idx in range(total_8x8_blocks):
        block_8x8_y = block_8x8_idx // BLOCKS_8X8_WIDTH
        block_8x8_x = block_8x8_idx % BLOCKS_8X8_WIDTH
        
        cur_start_y = block_8x8_y * 4
        cur_start_x = block_8x8_x * 4
        no_motion_updates = count_updated_2x2_blocks_no_motion(
            current_blocks, prev_blocks, cur_start_y, cur_start_x, diff_threshold
        )
        
        if no_motion_updates < min_improvement_threshold:
            early_skip_count += 1
            continue
        
        best_mv, mse, updates_needed, _ = hierarchical_diamond_search(
            current_blocks, prev_blocks, block_8x8_y, block_8x8_x, diff_threshold
        )
        
        improvement = no_motion_updates - updates_needed
        dx, dy = best_mv
        is_real_motion = (dx != 0 or dy != 0)
        has_significant_improvement = improvement >= min_improvement_threshold
        
        if (updates_needed <= update_threshold and
            is_real_motion and
            has_significant_improvement):
            
            zone_idx, zone_relative_idx = get_8x8_block_zone_info(block_8x8_idx)
            
            if zone_idx not in motion_candidates:
                motion_candidates[zone_idx] = []
            
            motion_candidates[zone_idx].append({
                'zone_relative_idx': zone_relative_idx,
                'motion_vector': best_mv,
                'updates_needed': updates_needed,
                'no_motion_updates': no_motion_updates,
                'improvement': improvement,
                'mse': mse,
                'block_8x8_pos': (block_8x8_y, block_8x8_x)
            })
        elif is_real_motion and not has_significant_improvement:
            motion_rejected_count += 1
    
    motion_stats.update_frame_stats(motion_candidates, total_8x8_blocks)
    motion_stats.motion_rejected_count += motion_rejected_count
    motion_stats.early_skip_count += early_skip_count
    
    return motion_candidates

def apply_motion_compensation_to_blocks(current_blocks: np.ndarray, prev_blocks: np.ndarray,
                                        motion_candidates: Dict) -> np.ndarray:
    compensated_blocks = prev_blocks.copy()
    
    for zone_idx, candidates in motion_candidates.items():
        for candidate in candidates:
            block_8x8_y, block_8x8_x = candidate['block_8x8_pos']
            dx, dy = candidate['motion_vector']
            
            cur_start_y = block_8x8_y * 4
            cur_start_x = block_8x8_x * 4
            
            ref_start_y = cur_start_y + dy // 2
            ref_start_x = cur_start_x + dx // 2
            
            blocks_h, blocks_w = prev_blocks.shape[:2]
            for dy_block in range(4):
                for dx_block in range(4):
                    cur_y = cur_start_y + dy_block
                    cur_x = cur_start_x + dx_block
                    ref_y = ref_start_y + dy_block
                    ref_x = ref_start_x + dx_block
                    
                    if (cur_y < blocks_h and cur_x < blocks_w and
                        0 <= ref_y < blocks_h and 0 <= ref_x < blocks_w):
                        compensated_blocks[cur_y, cur_x] = prev_blocks[ref_y, ref_x]
    
    return compensated_blocks

def merge_consecutive_motion_blocks(candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return []
    
    sorted_candidates = sorted(candidates, key=lambda x: x['zone_relative_idx'])
    
    merged_strips = []
    current_strip = None
    
    for candidate in sorted_candidates:
        zone_relative_idx = candidate['zone_relative_idx']
        motion_vector = candidate['motion_vector']
        block_8x8_y, block_8x8_x = candidate['block_8x8_pos']
        
        if current_strip is None:
            current_strip = {
                'zone_relative_idx': zone_relative_idx,
                'motion_vector': motion_vector,
                'count': 1,
                'start_x': block_8x8_x,
                'start_y': block_8x8_y
            }
        else:
            can_merge = (
                motion_vector == current_strip['motion_vector'] and
                block_8x8_y == current_strip['start_y'] and
                block_8x8_x == current_strip['start_x'] + current_strip['count'] and
                block_8x8_x < BLOCKS_8X8_WIDTH
            )
            
            if can_merge:
                current_strip['count'] += 1
            else:
                merged_strips.append({
                    'zone_relative_idx': current_strip['zone_relative_idx'],
                    'motion_vector': current_strip['motion_vector'],
                    'count': current_strip['count']
                })
                current_strip = {
                    'zone_relative_idx': zone_relative_idx,
                    'motion_vector': motion_vector,
                    'count': 1,
                    'start_x': block_8x8_x,
                    'start_y': block_8x8_y
                }
    
    if current_strip is not None:
        merged_strips.append({
            'zone_relative_idx': current_strip['zone_relative_idx'],
            'motion_vector': current_strip['motion_vector'],
            'count': current_strip['count']
        })
    
    return merged_strips

def encode_motion_compensation_data(motion_candidates: Dict) -> bytes:
    data = bytearray()
    
    zone_bitmap = 0
    for zone_idx in motion_candidates.keys():
        zone_bitmap |= (1 << zone_idx)
    
    data.append(zone_bitmap)
    
    total_strips = 0
    total_blocks_before_merge = 0
    total_blocks_after_merge = 0
    
    for zone_idx in range(TOTAL_ZONES):
        if zone_idx in motion_candidates:
            candidates = motion_candidates[zone_idx]
            total_blocks_before_merge += len(candidates)
            
            merged_strips = merge_consecutive_motion_blocks(candidates)
            total_strips += len(merged_strips)
            
            for strip in merged_strips:
                total_blocks_after_merge += strip['count']
            
            data.append(len(merged_strips))
            
            for strip in merged_strips:
                data.append(strip['zone_relative_idx'])
                dx, dy = strip['motion_vector']
                data.append(encode_motion_vector(dx, dy))
                data.append(strip['count'])
    
    motion_data = bytes(data)
    
    motion_stats.motion_data_bytes += len(motion_data)
    motion_stats.total_strips += total_strips
    motion_stats.blocks_before_merge += total_blocks_before_merge
    motion_stats.blocks_after_merge += total_blocks_after_merge
    
    return motion_data

class MotionCompensationStats:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_frames_processed = 0
        self.frames_with_motion_compensation = 0
        self.total_8x8_blocks_evaluated = 0
        self.total_8x8_blocks_compensated = 0
        self.motion_compensation_ratio = 0.0
        self.motion_rejected_count = 0
        self.motion_rejection_ratio = 0.0
        self.early_skip_count = 0
        self.early_skip_ratio = 0.0
        self.motion_vector_distribution = defaultdict(int)
        self.motion_magnitude_histogram = defaultdict(int)
        self.total_2x2_blocks_saved = 0
        self.average_blocks_saved_per_compensation = 0.0
        self.total_strips = 0
        self.blocks_before_merge = 0
        self.blocks_after_merge = 0
        self.merge_efficiency = 0.0
        self.zone_usage_count = defaultdict(int)
        self.motion_data_bytes = 0
        self.motion_data_ratio = 0.0
    
    def update_frame_stats(self, motion_candidates: Dict, total_8x8_blocks: int):
        self.total_frames_processed += 1
        self.total_8x8_blocks_evaluated += total_8x8_blocks
        
        if motion_candidates:
            self.frames_with_motion_compensation += 1
            compensated_blocks = 0
            blocks_saved = 0
            
            for zone_idx, candidates in motion_candidates.items():
                self.zone_usage_count[zone_idx] += 1
                compensated_blocks += len(candidates)
                
                for candidate in candidates:
                    dx, dy = candidate['motion_vector']
                    self.motion_vector_distribution[(dx, dy)] += 1
                    magnitude = int(np.sqrt(dx*dx + dy*dy))
                    self.motion_magnitude_histogram[magnitude] += 1
                    blocks_saved += (16 - candidate['updates_needed'])
            
            self.total_8x8_blocks_compensated += compensated_blocks
            self.total_2x2_blocks_saved += blocks_saved
    
    def update_data_size(self, motion_data_size: int, total_frame_size: int):
        self.motion_data_bytes += motion_data_size
        if total_frame_size > 0:
            self.motion_data_ratio = motion_data_size / total_frame_size
    
    def finalize_stats(self):
        if self.total_8x8_blocks_evaluated > 0:
            self.motion_compensation_ratio = self.total_8x8_blocks_compensated / self.total_8x8_blocks_evaluated
            self.early_skip_ratio = self.early_skip_count / self.total_8x8_blocks_evaluated
        if self.total_8x8_blocks_compensated > 0:
            self.average_blocks_saved_per_compensation = self.total_2x2_blocks_saved / self.total_8x8_blocks_compensated
        total_motion_attempts = self.total_8x8_blocks_compensated + self.motion_rejected_count
        if total_motion_attempts > 0:
            self.motion_rejection_ratio = self.motion_rejected_count / total_motion_attempts
        if self.blocks_before_merge > 0:
            self.merge_efficiency = (self.blocks_before_merge - self.total_strips) / self.blocks_before_merge
    
    def get_stats_dict(self) -> Dict:
        self.finalize_stats()
        top_motion_vectors = sorted(self.motion_vector_distribution.items(),
                                    key=lambda x: x[1], reverse=True)[:5]
        magnitude_stats = dict(sorted(self.motion_magnitude_histogram.items()))
        
        return {
            'frames': {
                'total_processed': self.total_frames_processed,
                'with_motion_compensation': self.frames_with_motion_compensation,
                'motion_compensation_frame_ratio': self.frames_with_motion_compensation / max(1, self.total_frames_processed)
            },
            'blocks': {
                'total_8x8_evaluated': self.total_8x8_blocks_evaluated,
                'total_8x8_compensated': self.total_8x8_blocks_compensated,
                'motion_compensation_ratio': self.motion_compensation_ratio,
                'motion_rejected_count': self.motion_rejected_count,
                'motion_rejection_ratio': self.motion_rejection_ratio,
                'early_skip_count': self.early_skip_count,
                'early_skip_ratio': self.early_skip_ratio,
                'total_2x2_blocks_saved': self.total_2x2_blocks_saved,
                'average_blocks_saved_per_compensation': self.average_blocks_saved_per_compensation
            },
            'motion_vectors': {
                'top_vectors': top_motion_vectors,
                'magnitude_distribution': magnitude_stats
            },
            'zones': {
                'usage_count': dict(self.zone_usage_count)
            },
            'merging': {
                'total_strips': self.total_strips,
                'blocks_before_merge': self.blocks_before_merge,
                'blocks_after_merge': self.blocks_after_merge,
                'merge_efficiency': self.merge_efficiency
            },
            'data_size': {
                'motion_data_bytes': self.motion_data_bytes,
                'motion_data_ratio': self.motion_data_ratio
            }
        }

motion_stats = MotionCompensationStats()

@njit(cache=True)
def calculate_2x2_block_difference_unified(current_block: np.ndarray, prev_block: np.ndarray) -> float:
    """
    Unified 2x2 block difference function, consistent with core_encoder.
    Computes mean squared error of Y channel.
    """
    y_diff_sum = 0.0
    for i in range(4):
        current_val = float(current_block[i])
        prev_val = float(prev_block[i])
        diff = current_val - prev_val
        y_diff_sum += diff * diff
    return y_diff_sum / 4.0
