#encoder/video_encoder_core.py

import numpy as np
import pathlib
import signal
from collections import defaultdict
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import pickle
from numba import njit

from core_encoder import *
from gop_processor import _progress_bar
from video_encoder_stats import EncodingStats
from video_encoder_utils import write_header, write_source
from motion_compensation import motion_stats

def _worker_init_ignore_sigint():
    import signal as _signal
    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)


def sort_single_gop_worker(args):
    gop_batch, frames, i_frame_interval, diff_threshold = args
    results = []
    for gop_start, gop_data in gop_batch:
        codebook = gop_data['unified_codebook'].copy()
        counts = np.zeros(len(codebook), dtype=int)
        gop_end = min(gop_start + i_frame_interval, len(frames))
        for fid in range(gop_start + 1, gop_end):
            cur = frames[fid]
            prev = frames[fid - 1]
            updated = identify_updated_big_blocks(cur, prev, diff_threshold)
            bt_map = None
            for fno, bt in gop_data['block_types_list']:
                if fno == fid:
                    bt_map = bt; break
            for by, bx in updated:
                is_color = bt_map and bt_map.get((by, bx), ('detail',))[0] == 'color'
                if not is_color:
                    for sy in (0,1):
                        for sx in (0,1):
                            y, x = by*2+sy, bx*2+sx
                            if y < cur.shape[0] and x < cur.shape[1]:
                                b = cur[y, x]
                                idx = quantize_blocks_unified(b.reshape(1, -1), codebook)[0]
                                counts[idx] += 1
        max_count = counts.max()
        min_count = counts.min()
        total_usage = counts.sum()
        if max_count > min_count and total_usage > 0:
            order = np.argsort(-counts, kind='stable')
            gop_data['unified_codebook'] = codebook[order]
            index_mapping = np.zeros(len(codebook), dtype=int)
            for new_idx, old_idx in enumerate(order):
                index_mapping[old_idx] = new_idx
            for fid, bt in gop_data['block_types_list']:
                if bt is not None:
                    for (big_by, big_bx), (block_type, block_indices) in bt.items():
                        if block_type == 'detail':
                            new_indices = []
                            for old_idx in block_indices:
                                if old_idx < len(index_mapping):
                                    new_indices.append(index_mapping[old_idx])
                                else:
                                    new_indices.append(old_idx)
                            bt[(big_by, big_bx)] = (block_type, new_indices)
        results.append((gop_start, gop_data))
    return results


def sort_single_gop_worker_sliced(args):
    adjusted_batch, frames_slice, i_frame_interval, diff_threshold, first_frame = args
    results = []
    for rel_gop_start, gop_data in adjusted_batch:
        abs_gop_start = rel_gop_start + first_frame
        codebook = gop_data['unified_codebook'].copy()
        counts = np.zeros(len(codebook), dtype=int)
        gop_end = min(rel_gop_start + i_frame_interval, len(frames_slice))
        for fid in range(rel_gop_start + 1, gop_end):
            cur = frames_slice[fid]
            prev = frames_slice[fid - 1]
            updated = identify_updated_big_blocks(cur, prev, diff_threshold)
            bt_map = None
            abs_fid = fid + first_frame
            for fno, bt in gop_data['block_types_list']:
                if fno == abs_fid:
                    bt_map = bt
                    break
            for by, bx in updated:
                is_color = bt_map and bt_map.get((by, bx), ('detail',))[0] == 'color'
                if not is_color:
                    for sy in (0, 1):
                        for sx in (0, 1):
                            y, x = by*2+sy, bx*2+sx
                            if y < cur.shape[0] and x < cur.shape[1]:
                                b = cur[y, x]
                                idx = quantize_blocks_unified(b.reshape(1, -1), codebook)[0]
                                counts[idx] += 1
        max_count = counts.max()
        min_count = counts.min()
        total_usage = counts.sum()
        if max_count > min_count and total_usage > 0:
            order = np.argsort(-counts, kind='stable')
            gop_data['unified_codebook'] = codebook[order]
            index_mapping = np.zeros(len(codebook), dtype=int)
            for new_idx, old_idx in enumerate(order):
                index_mapping[old_idx] = new_idx
            for fid, bt in gop_data['block_types_list']:
                if bt is not None:
                    for (big_by, big_bx), (block_type, block_indices) in bt.items():
                        if block_type == 'detail':
                            new_indices = [
                                index_mapping[old_idx] if old_idx < len(index_mapping) else old_idx
                                for old_idx in block_indices
                            ]
                            bt[(big_by, big_bx)] = (block_type, new_indices)
        results.append((abs_gop_start, gop_data))
    return results

class SimpleStats:
    def __init__(self):
        self.total_frames = 0
        self.i_frames = 0
        self.p_frames = 0
        self.forced_i_frames = 0
        self.threshold_i_frames = 0
        self.i_frame_bytes = 0
        self.p_frame_bytes = 0
        self.codebook_bytes = 0
        self.index_bytes = 0
        self.p_overhead_bytes = 0
        self.small_updates = 0
        self.medium_updates = 0
        self.full_updates = 0
        self.small_bytes = 0
        self.medium_bytes = 0
        self.full_bytes = 0
        self.small_segments = {}
        self.medium_segments = {}
        self.small_blocks_per_update = []
        self.medium_blocks_per_update = []
        self.full_blocks_per_update = []
        self.small_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        self.medium_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        self.full_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        self.motion_stats_dict = None

def encode_frame_chunk_worker(args):
    import pickle as _pickle
    import os as _os

    (start_idx, end_idx, frames_chunk_or_ref, gop_codebooks_chunk, i_frame_interval,
     diff_threshold, force_i_threshold, enabled_segments_bitmap,
     enabled_medium_segments_bitmap, codebook_size, color_fallback_threshold,
     motion_compensation_enabled, motion_update_threshold, progress_queue) = args

    if isinstance(frames_chunk_or_ref, tuple) and len(frames_chunk_or_ref) == 5:
        mmap_path, shape, dtype_str, slice_start, slice_end = frames_chunk_or_ref
        _mmap = np.memmap(mmap_path, dtype=np.dtype(dtype_str), mode='r', shape=shape)
        frames_chunk = [_mmap[i].copy() for i in range(slice_start, slice_end)]
        del _mmap
    else:
        frames_chunk = frames_chunk_or_ref

    motion_stats.reset()
    encoded_frames = []
    frame_offsets = []
    current_offset = 0
    prev_frame = None
    local_stats = SimpleStats()

    _cached_gop_start = None
    _cached_codebook = None
    _cached_block_types_map = {}

    for frame_idx in range(start_idx, end_idx):
        if frame_idx >= len(frames_chunk) + start_idx:
            break

        current_frame = frames_chunk[frame_idx - start_idx]
        frame_offsets.append(current_offset)

        gop_start = (frame_idx // i_frame_interval) * i_frame_interval

        if gop_start != _cached_gop_start:
            gop_path = gop_codebooks_chunk.get(gop_start)
            if gop_path and _os.path.exists(gop_path):
                with open(gop_path, 'rb') as _f:
                    gop_data = _pickle.load(_f)
                _cached_codebook = gop_data['unified_codebook']
                _cached_block_types_map = {fid: bt for fid, bt in gop_data['block_types_list']}
                del gop_data
            else:
                _cached_codebook = np.zeros((codebook_size, 12), dtype=np.uint8)
                _cached_block_types_map = {}
            _cached_gop_start = gop_start

        unified_codebook = _cached_codebook
        block_types = _cached_block_types_map.get(frame_idx)
        if block_types is None:
            _, block_types = classify_4x4_blocks_unified(current_frame, 5.0)

        force_i_frame = (frame_idx % i_frame_interval == 0) or frame_idx == 0

        if force_i_frame or prev_frame is None:
            frame_data = encode_i_frame_unified(
                current_frame, unified_codebook, block_types, color_fallback_threshold)
            is_i_frame = True
            OUTPUT_BYTES_PER_BLOCK = 6
            codebook_size_bytes = codebook_size * OUTPUT_BYTES_PER_BLOCK
            index_size = len(frame_data) - 1 - codebook_size_bytes
            local_stats.total_frames += 1
            local_stats.i_frames += 1
            if force_i_frame:
                local_stats.forced_i_frames += 1
            else:
                local_stats.threshold_i_frames += 1
            local_stats.i_frame_bytes += len(frame_data)
            local_stats.codebook_bytes += codebook_size_bytes
            local_stats.index_bytes += max(0, index_size)
        else:
            accumulated_frame = accumulate_unchanged_blocks(current_frame, prev_frame, diff_threshold)
            (frame_data, is_i_frame, used_zones, color_updates, detail_updates,
             small_updates, medium_updates, full_updates,
             small_bytes, medium_bytes, full_bytes,
             small_segments, medium_segments,
             small_blocks_per_update, medium_blocks_per_update,
             full_blocks_per_update) = encode_p_frame_unified(
                accumulated_frame, prev_frame, unified_codebook, block_types,
                diff_threshold, force_i_threshold, enabled_segments_bitmap,
                enabled_medium_segments_bitmap, color_fallback_threshold,
                motion_compensation_enabled, motion_update_threshold)

            if is_i_frame:
                OUTPUT_BYTES_PER_BLOCK = 6
                codebook_size_bytes = codebook_size * OUTPUT_BYTES_PER_BLOCK
                index_size = len(frame_data) - 1 - codebook_size_bytes
                local_stats.total_frames += 1
                local_stats.i_frames += 1
                local_stats.threshold_i_frames += 1
                local_stats.i_frame_bytes += len(frame_data)
                local_stats.codebook_bytes += codebook_size_bytes
                local_stats.index_bytes += max(0, index_size)
            else:
                local_stats.total_frames += 1
                local_stats.p_frames += 1
                local_stats.p_frame_bytes += len(frame_data)
                local_stats.small_updates += small_updates
                local_stats.medium_updates += medium_updates
                local_stats.full_updates += full_updates
                local_stats.small_bytes += small_bytes
                local_stats.medium_bytes += medium_bytes
                local_stats.full_bytes += full_bytes
                for seg_idx, count in small_segments.items():
                    local_stats.small_segments[seg_idx] = local_stats.small_segments.get(seg_idx, 0) + count
                for seg_idx, count in medium_segments.items():
                    local_stats.medium_segments[seg_idx] = local_stats.medium_segments.get(seg_idx, 0) + count
                local_stats.small_blocks_per_update.extend(small_blocks_per_update)
                local_stats.medium_blocks_per_update.extend(medium_blocks_per_update)
                local_stats.full_blocks_per_update.extend(full_blocks_per_update)
                for bc in small_blocks_per_update:
                    if 1 <= bc <= 4: local_stats.small_blocks_distribution[bc] += 1
                for bc in medium_blocks_per_update:
                    if 1 <= bc <= 4: local_stats.medium_blocks_distribution[bc] += 1
                for bc in full_blocks_per_update:
                    if 1 <= bc <= 4: local_stats.full_blocks_distribution[bc] += 1

        encoded_frames.append(frame_data)
        current_offset += len(frame_data)

        if force_i_frame or prev_frame is None:
            prev_frame = current_frame.copy() if current_frame.size > 0 else None
        else:
            prev_frame = accumulated_frame.copy() if accumulated_frame.size > 0 else None

        if progress_queue is not None:
            try:
                progress_queue.put_nowait(1)
            except Exception:
                pass
    local_stats.motion_stats_dict = motion_stats.get_stats_dict()
    return encoded_frames, frame_offsets, start_idx, local_stats

class VideoEncoderCore:
    def __init__(self):
        self.encoding_stats = EncodingStats()
    
    def encode_video(self, frames, output_path, i_frame_interval=60, diff_threshold=2.0,
                    force_i_threshold=0.7, variance_threshold=5.0, color_fallback_threshold=50.0,
                    codebook_size=256, kmeans_max_iter=200, i_frame_weight=3, max_workers=None,
                    enabled_segments_bitmap=0xFFFF, enabled_medium_segments_bitmap=0x0F,
                    fps=30.0, motion_compensation_enabled=True, motion_update_threshold=8):
        from gop_processor import generate_gop_unified_codebooks

        if max_workers is None:
            max_workers = mp.cpu_count()

        num_frames = len(frames)
        print(f"Codebook: {codebook_size} entries  |  Workers: {max_workers}  |  Frames: {num_frames}", flush=True)

        start_time = time.time()

        tmp_dir = str(pathlib.Path(__file__).parent.parent / "temp")
        try:
            gop_codebook_paths = generate_gop_unified_codebooks(
                frames, i_frame_interval,
                variance_threshold, diff_threshold, codebook_size,
                kmeans_max_iter, i_frame_weight, max_workers,
                tmp_dir=tmp_dir
            )
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted during codebook generation")
            raise

        print("Training codebook: sorting by usage frequency...", flush=True)
        try:
            self._sort_codebooks_on_disk(
                frames, gop_codebook_paths, i_frame_interval, diff_threshold
            )
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted during codebook sorting")
            raise

        print("Encoding frames...", flush=True)
        try:
            encoded_frames, frame_offsets = self._parallel_encode_frames(
                frames, gop_codebook_paths, i_frame_interval, diff_threshold, force_i_threshold,
                enabled_segments_bitmap, enabled_medium_segments_bitmap, codebook_size,
                color_fallback_threshold, motion_compensation_enabled, motion_update_threshold, max_workers
            )
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted during frame encoding")
            raise

        elapsed = time.time() - start_time
        print(f"\nDone. Elapsed: {elapsed:.2f}s")

        all_data = b''.join(encoded_frames)

        i_frame_timestamps = [i / fps for i in range(0, num_frames, i_frame_interval)]

        output_path_obj = pathlib.Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        include_dir = pathlib.Path(__file__).parent.parent / "include" / "video"
        include_dir.mkdir(parents=True, exist_ok=True)
        write_header(include_dir / "video_data.h", num_frames, len(all_data), codebook_size, fps)
        write_source(output_path_obj.with_suffix(".bin"), all_data, frame_offsets)

        self.encoding_stats.print_summary(num_frames, len(all_data))

        return all_data, frame_offsets, i_frame_timestamps
    
    def _sort_codebooks_on_disk(self, frames, gop_codebook_paths, i_frame_interval, diff_threshold):
        import pickle
        total_gops = len(gop_codebook_paths)
        done = 0
        for gop_start, pkl_path in sorted(gop_codebook_paths.items()):
            if pkl_path is None or not pathlib.Path(pkl_path).exists():
                done += 1
                continue

            with open(pkl_path, 'rb') as f:
                gop_data = pickle.load(f)

            codebook = gop_data['unified_codebook'].copy()
            counts = np.zeros(len(codebook), dtype=int)
            gop_end = min(gop_start + i_frame_interval, len(frames))

            for fid in range(gop_start + 1, gop_end):
                cur = np.array(frames[fid])
                prev = np.array(frames[fid - 1])
                updated = identify_updated_big_blocks(cur, prev, diff_threshold)
                bt_map = None
                for fno, bt in gop_data['block_types_list']:
                    if fno == fid:
                        bt_map = bt
                        break
                for by, bx in updated:
                    is_color = bt_map and bt_map.get((by, bx), ('detail',))[0] == 'color'
                    if not is_color:
                        for sy in (0, 1):
                            for sx in (0, 1):
                                y, x = by*2+sy, bx*2+sx
                                if y < cur.shape[0] and x < cur.shape[1]:
                                    b = cur[y, x]
                                    idx = quantize_blocks_unified(b.reshape(1, -1), codebook)[0]
                                    counts[idx] += 1

            if counts.max() > counts.min() and counts.sum() > 0:
                order = np.argsort(-counts, kind='stable')
                gop_data['unified_codebook'] = codebook[order]
                index_mapping = np.zeros(len(codebook), dtype=int)
                for new_idx, old_idx in enumerate(order):
                    index_mapping[old_idx] = new_idx
                for fid, bt in gop_data['block_types_list']:
                    if bt is not None:
                        for key, (btype, bindices) in bt.items():
                            if btype == 'detail':
                                bt[key] = (btype, [
                                    index_mapping[i] if i < len(index_mapping) else i
                                    for i in bindices
                                ])

            with open(pkl_path, 'wb') as f:
                pickle.dump(gop_data, f, protocol=4)
            del gop_data, codebook, counts

            done += 1
            _progress_bar(done, total_gops, prefix="Sorting codebooks ")
        print()
    
    def _parallel_encode_frames(self, frames, gop_codebook_paths, i_frame_interval, diff_threshold, 
                               force_i_threshold, enabled_segments_bitmap, enabled_medium_segments_bitmap, 
                               codebook_size, color_fallback_threshold, motion_compensation_enabled, 
                               motion_update_threshold, max_workers):
        import pickle
        num_frames = len(frames)
        num_gops = (num_frames + i_frame_interval - 1) // i_frame_interval
        
        frames_is_mmap = hasattr(frames, 'filename')

        if num_gops <= max_workers:
            gop_per_worker = max(1, num_gops // max_workers)
            chunk_data_list = []

            for i in range(0, num_gops, gop_per_worker):
                end_gop = min(i + gop_per_worker, num_gops)
                start_frame = i * i_frame_interval
                end_frame = min(end_gop * i_frame_interval, num_frames)

                if frames_is_mmap:
                    frames_chunk = (frames.filename, frames.shape, frames.dtype.str, start_frame, end_frame)
                else:
                    frames_chunk = frames[start_frame:end_frame]

                gop_paths_chunk = {
                    gop_start: gop_codebook_paths[gop_start]
                    for gop_start in range(i * i_frame_interval, end_gop * i_frame_interval, i_frame_interval)
                    if gop_start in gop_codebook_paths
                }

                chunk_data = (start_frame, end_frame, frames_chunk, gop_paths_chunk, i_frame_interval,
                            diff_threshold, force_i_threshold, enabled_segments_bitmap,
                            enabled_medium_segments_bitmap, codebook_size, color_fallback_threshold,
                            motion_compensation_enabled, motion_update_threshold)
                chunk_data_list.append(chunk_data)
        else:
            frames_per_worker = max(i_frame_interval, num_frames // max_workers)
            frames_per_worker = ((frames_per_worker + i_frame_interval - 1) // i_frame_interval) * i_frame_interval

            chunk_data_list = []
            for i in range(0, num_frames, frames_per_worker):
                end_frame = min(i + frames_per_worker, num_frames)

                if frames_is_mmap:
                    frames_chunk = (frames.filename, frames.shape, frames.dtype.str, i, end_frame)
                else:
                    frames_chunk = frames[i:end_frame]

                start_gop = i // i_frame_interval
                end_gop = (end_frame + i_frame_interval - 1) // i_frame_interval

                gop_paths_chunk = {
                    gop_start: gop_codebook_paths[gop_start]
                    for gop_start in range(start_gop * i_frame_interval, end_gop * i_frame_interval, i_frame_interval)
                    if gop_start in gop_codebook_paths
                }

                chunk_data = (i, end_frame, frames_chunk, gop_paths_chunk, i_frame_interval,
                            diff_threshold, force_i_threshold, enabled_segments_bitmap,
                            enabled_medium_segments_bitmap, codebook_size, color_fallback_threshold,
                            motion_compensation_enabled, motion_update_threshold)
                chunk_data_list.append(chunk_data)
        
        print(f"Parallel encoding: {len(chunk_data_list)} chunks, ~{len(frames) // len(chunk_data_list)} frames each", flush=True)
        
        total_frames = len(frames)
        
        chunk_data_list = [chunk + (None,) for chunk in chunk_data_list]
        
        with ProcessPoolExecutor(max_workers=min(len(chunk_data_list), max_workers),
                                 initializer=_worker_init_ignore_sigint) as executor:
            futures = [executor.submit(encode_frame_chunk_worker, chunk_data) for chunk_data in chunk_data_list]
            
            try:
                import time as _time
                while True:
                    done_count = sum(1 for f in futures if f.done())
                    done_frames = int(done_count / len(futures) * total_frames)
                    _progress_bar(done_frames, total_frames, prefix="Encoding frames ")
                    if done_count == len(futures):
                        _progress_bar(total_frames, total_frames, prefix="Encoding frames ")
                        break
                    _time.sleep(0.5)

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted — cancelling frame encoding...")
                for f in futures:
                    f.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                raise

            print()
            
            results = [f.result() for f in futures]
            results.sort(key=lambda x: x[2])
            
            all_encoded_frames = []
            all_frame_offsets = []
            current_offset = 0
            
            for encoded_frames, frame_offsets, _, local_stats in results:
                all_encoded_frames.extend(encoded_frames)
                adjusted_offsets = [current_offset + offset for offset in frame_offsets]
                all_frame_offsets.extend(adjusted_offsets)
                current_offset += sum(len(frame_data) for frame_data in encoded_frames)
                
                self.encoding_stats.total_frames_processed += local_stats.total_frames
                self.encoding_stats.total_i_frames += local_stats.i_frames
                self.encoding_stats.total_p_frames += local_stats.p_frames
                self.encoding_stats.forced_i_frames += local_stats.forced_i_frames
                self.encoding_stats.threshold_i_frames += local_stats.threshold_i_frames
                self.encoding_stats.total_i_frame_bytes += local_stats.i_frame_bytes
                self.encoding_stats.total_p_frame_bytes += local_stats.p_frame_bytes
                self.encoding_stats.total_codebook_bytes += local_stats.codebook_bytes
                self.encoding_stats.total_index_bytes += local_stats.index_bytes
                self.encoding_stats.small_codebook_updates += local_stats.small_updates
                self.encoding_stats.medium_codebook_updates += local_stats.medium_updates
                self.encoding_stats.full_codebook_updates += local_stats.full_updates
                self.encoding_stats.small_codebook_bytes += local_stats.small_bytes
                self.encoding_stats.medium_codebook_bytes += local_stats.medium_bytes
                self.encoding_stats.full_codebook_bytes += local_stats.full_bytes
                for seg_idx, count in local_stats.small_segments.items():
                    self.encoding_stats.small_segment_usage[seg_idx] += count
                for seg_idx, count in local_stats.medium_segments.items():
                    self.encoding_stats.medium_segment_usage[seg_idx] += count
                self.encoding_stats.small_codebook_blocks_per_update.extend(local_stats.small_blocks_per_update)
                self.encoding_stats.medium_codebook_blocks_per_update.extend(local_stats.medium_blocks_per_update)
                self.encoding_stats.full_codebook_blocks_per_update.extend(local_stats.full_blocks_per_update)
                for block_count in [1, 2, 3, 4]:
                    self.encoding_stats.small_blocks_distribution[block_count] += local_stats.small_blocks_distribution.get(block_count, 0)
                    self.encoding_stats.medium_blocks_distribution[block_count] += local_stats.medium_blocks_distribution.get(block_count, 0)
                    self.encoding_stats.full_blocks_distribution[block_count] += local_stats.full_blocks_distribution.get(block_count, 0)
                if local_stats.motion_stats_dict is not None:
                    self.encoding_stats.merge_motion_compensation_stats(local_stats.motion_stats_dict)
        
        return all_encoded_frames, all_frame_offsets
