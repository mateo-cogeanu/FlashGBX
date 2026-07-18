#encoder/video_encoder_stats.py

import statistics
from collections import defaultdict
from motion_compensation import motion_stats

class EncodingStats:
    def __init__(self):
        self.total_frames_processed = 0
        self.total_i_frames = 0
        self.forced_i_frames = 0
        self.threshold_i_frames = 0
        self.total_p_frames = 0
        
        self.total_i_frame_bytes = 0
        self.total_p_frame_bytes = 0
        self.total_codebook_bytes = 0
        self.total_index_bytes = 0
        self.total_p_overhead_bytes = 0
        
        self.p_frame_updates = []
        self.zone_usage = defaultdict(int)
        
        self.color_block_bytes = 0
        self.detail_block_bytes = 0
        self.color_update_count = 0
        self.detail_update_count = 0
        
        self.small_codebook_updates = 0
        self.medium_codebook_updates = 0
        self.full_codebook_updates = 0
        self.small_codebook_bytes = 0
        self.medium_codebook_bytes = 0
        self.full_codebook_bytes = 0
        
        self.small_segment_usage = defaultdict(int)
        self.medium_segment_usage = defaultdict(int)
        
        self.small_codebook_blocks_per_update = []
        self.medium_codebook_blocks_per_update = []
        self.full_codebook_blocks_per_update = []
        
        self.small_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        self.medium_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        self.full_blocks_distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        
        self.motion_compensation_stats = None
    
    def add_i_frame(self, size_bytes, is_forced=True, codebook_size=0, index_size=0):
        self.total_frames_processed += 1
        self.total_i_frames += 1
        if is_forced:
            self.forced_i_frames += 1
        else:
            self.threshold_i_frames += 1
        self.total_i_frame_bytes += size_bytes
        self.total_codebook_bytes += codebook_size
        self.total_index_bytes += index_size
    
    def add_p_frame(self, size_bytes, updates_count, zone_count,
                    color_updates=0, detail_updates=0,
                    small_updates=0, medium_updates=0, full_updates=0,
                    small_bytes=0, medium_bytes=0, full_bytes=0,
                    small_segments=None, medium_segments=None,
                    small_blocks_per_update=None, medium_blocks_per_update=None,
                    full_blocks_per_update=None):
        self.total_frames_processed += 1
        self.total_p_frames += 1
        self.total_p_frame_bytes += size_bytes
        self.p_frame_updates.append(updates_count)
        self.zone_usage[zone_count] += 1
        
        overhead = 3 + zone_count * 2
        self.total_p_overhead_bytes += overhead
        
        self.color_update_count += color_updates
        self.detail_update_count += detail_updates
        
        self.small_codebook_updates += small_updates
        self.medium_codebook_updates += medium_updates
        self.full_codebook_updates += full_updates
        self.small_codebook_bytes += small_bytes
        self.medium_codebook_bytes += medium_bytes
        self.full_codebook_bytes += full_bytes
        
        if small_segments:
            for seg_idx, count in small_segments.items():
                self.small_segment_usage[seg_idx] += count
        if medium_segments:
            for seg_idx, count in medium_segments.items():
                self.medium_segment_usage[seg_idx] += count
        
        if small_blocks_per_update:
            for block_count in small_blocks_per_update:
                if 1 <= block_count <= 4:
                    self.small_blocks_distribution[block_count] += 1
        if medium_blocks_per_update:
            for block_count in medium_blocks_per_update:
                if 1 <= block_count <= 4:
                    self.medium_blocks_distribution[block_count] += 1
        if full_blocks_per_update:
            for block_count in full_blocks_per_update:
                if 1 <= block_count <= 4:
                    self.full_blocks_distribution[block_count] += 1
    
    def print_summary(self, total_frames, total_bytes):
        print(f"\n📊 Encoding Statistics Report")
        print(f"=" * 60)
        
        print(f"🎬 Frame stats:")
        print(f"   Total frames: {total_frames}")
        print(f"   I-frames: {self.total_i_frames} ({self.total_i_frames/total_frames*100:.1f}%)")
        print(f"     - Forced (GOP boundary): {self.forced_i_frames}")
        print(f"     - Threshold-triggered:   {self.threshold_i_frames}")
        print(f"   P-frames: {self.total_p_frames} ({self.total_p_frames/total_frames*100:.1f}%)")
        
        print(f"\n💾 Size breakdown:")
        print(f"   Total: {total_bytes:,} bytes ({total_bytes/1024:.1f} KB)")
        print(f"   I-frame data: {self.total_i_frame_bytes:,} bytes ({self.total_i_frame_bytes/total_bytes*100:.1f}%)")
        print(f"   P-frame data: {self.total_p_frame_bytes:,} bytes ({self.total_p_frame_bytes/total_bytes*100:.1f}%)")
        
        if self.total_i_frames > 0:
            print(f"   Avg I-frame size: {self.total_i_frame_bytes/self.total_i_frames:.1f} bytes")
        if self.total_p_frames > 0:
            print(f"   Avg P-frame size: {self.total_p_frame_bytes/self.total_p_frames:.1f} bytes")
        
        print(f"\n🎨 Data composition:")
        print(f"   Codebook data:    {self.total_codebook_bytes:,} bytes ({self.total_codebook_bytes/total_bytes*100:.1f}%)")
        print(f"   I-frame indices:  {self.total_index_bytes:,} bytes ({self.total_index_bytes/total_bytes*100:.1f}%)")
        p_frame_data_bytes = self.total_p_frame_bytes - self.total_p_overhead_bytes
        print(f"   P-frame updates:  {p_frame_data_bytes:,} bytes ({p_frame_data_bytes/total_bytes*100:.1f}%)")
        print(f"   P-frame overhead: {self.total_p_overhead_bytes:,} bytes ({self.total_p_overhead_bytes/total_bytes*100:.1f}%)")
        
        total_detail_updates = self.small_codebook_updates + self.medium_codebook_updates + self.full_codebook_updates
        if total_detail_updates > 0:
            print(f"\n📚 Codebook usage:")
            print(f"   Small  (u4): {self.small_codebook_updates:,} ({self.small_codebook_updates/total_detail_updates*100:.1f}%)")
            print(f"   Medium (u6): {self.medium_codebook_updates:,} ({self.medium_codebook_updates/total_detail_updates*100:.1f}%)")
            print(f"   Full   (u8): {self.full_codebook_updates:,} ({self.full_codebook_updates/total_detail_updates*100:.1f}%)")
            
            total_codebook_data = self.small_codebook_bytes + self.medium_codebook_bytes + self.full_codebook_bytes
            if total_codebook_data > 0:
                print(f"\n💾 Codebook data sizes:")
                print(f"   Small:  {self.small_codebook_bytes:,} bytes ({self.small_codebook_bytes/total_codebook_data*100:.1f}%)")
                print(f"   Medium: {self.medium_codebook_bytes:,} bytes ({self.medium_codebook_bytes/total_codebook_data*100:.1f}%)")
                print(f"   Full:   {self.full_codebook_bytes:,} bytes ({self.full_codebook_bytes/total_codebook_data*100:.1f}%)")
            
            print(f"\n📊 Block count distribution per update:")
            if self.small_codebook_updates > 0:
                print(f"   Small codebook:")
                for bc in [1, 2, 3, 4]:
                    count = self.small_blocks_distribution[bc]
                    print(f"     {bc} block(s): {count} ({count/self.small_codebook_updates*100:.1f}%)")
            if self.medium_codebook_updates > 0:
                print(f"   Medium codebook:")
                for bc in [1, 2, 3, 4]:
                    count = self.medium_blocks_distribution[bc]
                    print(f"     {bc} block(s): {count} ({count/self.medium_codebook_updates*100:.1f}%)")
            if self.full_codebook_updates > 0:
                print(f"   Full codebook:")
                for bc in [1, 2, 3, 4]:
                    count = self.full_blocks_distribution[bc]
                    print(f"     {bc} block(s): {count} ({count/self.full_codebook_updates*100:.1f}%)")
        
        if self.small_segment_usage:
            print(f"\n🔢 Small codebook segment usage:")
            total_small = sum(self.small_segment_usage.values())
            for seg_idx in sorted(self.small_segment_usage.keys()):
                usage = self.small_segment_usage[seg_idx]
                print(f"   Seg {seg_idx}: {usage} ({usage/self.small_codebook_updates*100:.1f}%)")
            first_4 = sum(self.small_segment_usage.get(i, 0) for i in range(4))
            if total_small > 0:
                print(f"   First 4 segments: {first_4/total_small*100:.1f}% (sort effectiveness)")
        
        if self.medium_segment_usage:
            print(f"\n🔢 Medium codebook segment usage:")
            total_medium = sum(self.medium_segment_usage.values())
            for seg_idx in sorted(self.medium_segment_usage.keys()):
                usage = self.medium_segment_usage[seg_idx]
                print(f"   Seg {seg_idx}: {usage} ({usage/self.medium_codebook_updates*100:.1f}%)")
            first_2 = sum(self.medium_segment_usage.get(i, 0) for i in range(2))
            if total_medium > 0:
                print(f"   First 2 segments: {first_2/total_medium*100:.1f}% (sort effectiveness)")
        
        if self.p_frame_updates:
            avg_updates = statistics.mean(self.p_frame_updates)
            median_updates = statistics.median(self.p_frame_updates)
            print(f"\n⚡ P-frame update analysis:")
            print(f"   Median updated blocks: {median_updates:.1f}")
            print(f"   Max updated blocks:    {max(self.p_frame_updates)}")
            print(f"   Min updated blocks:    {min(self.p_frame_updates)}")
            print(f"   Color block updates:   {self.color_update_count:,}")
            print(f"   Texture block updates: {self.detail_update_count:,}")
        
        if self.zone_usage:
            print(f"\n🗺️  Zone usage distribution:")
            total_zones_used = sum(self.zone_usage.values())
            for zone_count in sorted(self.zone_usage.keys()):
                usage = self.zone_usage[zone_count]
                print(f"   {zone_count} zone(s): {usage} ({usage/total_zones_used*100:.1f}%)")
        
        original_size = total_frames * 240 * 160 * 3
        compression_ratio = original_size / total_bytes
        compression_rate = (1 - total_bytes / original_size) * 100
        
        print(f"\n📈 Compression efficiency:")
        print(f"   Estimated raw size: {original_size:,} bytes ({original_size/1024/1024:.1f} MB)")
        print(f"   Compression ratio:  {compression_ratio:.1f}:1")
        print(f"   Compression rate:   {compression_rate:.1f}%")
        
        if self.motion_compensation_stats is not None:
            self.finalize_motion_compensation_stats()
            self._print_motion_compensation_stats(self.motion_compensation_stats)
    
    def _print_motion_compensation_stats(self, mc_stats):
        print(f"\n🎯 Motion Compensation Statistics:")
        print(f"=" * 60)
        
        frames = mc_stats['frames']
        print(f"📺 Frames:")
        print(f"   Processed: {frames['total_processed']}")
        print(f"   With motion compensation: {frames['with_motion_compensation']} ({frames['motion_compensation_frame_ratio']*100:.1f}%)")
        
        blocks = mc_stats['blocks']
        print(f"\n🔲 Blocks:")
        print(f"   8x8 blocks evaluated:    {blocks['total_8x8_evaluated']:,}")
        print(f"   8x8 blocks compensated:  {blocks['total_8x8_compensated']:,} ({blocks['motion_compensation_ratio']*100:.1f}%)")
        print(f"   2x2 blocks saved:        {blocks['total_2x2_blocks_saved']:,}")
        if blocks['total_8x8_compensated'] > 0:
            print(f"   Avg saved per compensation: {blocks['average_blocks_saved_per_compensation']:.1f}")
        
        if 'merging' in mc_stats and mc_stats['merging']['blocks_before_merge'] > 0:
            m = mc_stats['merging']
            print(f"\n🔗 Strip merging:")
            print(f"   Blocks before merge: {m['blocks_before_merge']:,}")
            print(f"   Strips after merge:  {m['total_strips']:,}")
            print(f"   Merge efficiency:    {m['merge_efficiency']*100:.1f}%")
        
        mv = mc_stats['motion_vectors']
        if mv['top_vectors']:
            print(f"\n🎯 Top motion vectors:")
            for i, ((dx, dy), count) in enumerate(mv['top_vectors'][:5]):
                print(f"   {i+1}. ({dx:+3d}, {dy:+3d}): {count:,}")
        
        data_size = mc_stats['data_size']
        if data_size['motion_data_bytes'] > 0:
            print(f"\n💾 Motion data: {data_size['motion_data_bytes']:,} bytes ({data_size['motion_data_bytes']/1024:.1f} KB)")
    
    def merge_stats(self, other_stats):
        self.total_frames_processed += other_stats.total_frames_processed
        self.total_i_frames += other_stats.total_i_frames
        self.forced_i_frames += other_stats.forced_i_frames
        self.threshold_i_frames += other_stats.threshold_i_frames
        self.total_p_frames += other_stats.total_p_frames
        self.total_i_frame_bytes += other_stats.total_i_frame_bytes
        self.total_p_frame_bytes += other_stats.total_p_frame_bytes
        self.total_codebook_bytes += other_stats.total_codebook_bytes
        self.total_index_bytes += other_stats.total_index_bytes
        self.total_p_overhead_bytes += other_stats.total_p_overhead_bytes
        self.p_frame_updates.extend(other_stats.p_frame_updates)
        for zone_count, usage_count in other_stats.zone_usage.items():
            self.zone_usage[zone_count] += usage_count
        self.color_block_bytes += other_stats.color_block_bytes
        self.detail_block_bytes += other_stats.detail_block_bytes
        self.color_update_count += other_stats.color_update_count
        self.detail_update_count += other_stats.detail_update_count
        self.small_codebook_updates += other_stats.small_codebook_updates
        self.medium_codebook_updates += other_stats.medium_codebook_updates
        self.full_codebook_updates += other_stats.full_codebook_updates
        self.small_codebook_bytes += other_stats.small_codebook_bytes
        self.medium_codebook_bytes += other_stats.medium_codebook_bytes
        self.full_codebook_bytes += other_stats.full_codebook_bytes
        for seg_idx, count in other_stats.small_segment_usage.items():
            self.small_segment_usage[seg_idx] += count
        for seg_idx, count in other_stats.medium_segment_usage.items():
            self.medium_segment_usage[seg_idx] += count
        self.small_codebook_blocks_per_update.extend(other_stats.small_codebook_blocks_per_update)
        self.medium_codebook_blocks_per_update.extend(other_stats.medium_codebook_blocks_per_update)
        self.full_codebook_blocks_per_update.extend(other_stats.full_codebook_blocks_per_update)
        for bc in [1, 2, 3, 4]:
            self.small_blocks_distribution[bc] += other_stats.small_blocks_distribution.get(bc, 0)
            self.medium_blocks_distribution[bc] += other_stats.medium_blocks_distribution.get(bc, 0)
            self.full_blocks_distribution[bc] += other_stats.full_blocks_distribution.get(bc, 0)
    
    def merge_motion_compensation_stats(self, motion_stats_dict):
        if motion_stats_dict is None:
            return
        
        if self.motion_compensation_stats is None:
            self.motion_compensation_stats = {
                'frames': {'total_processed': 0, 'with_motion_compensation': 0, 'motion_compensation_frame_ratio': 0.0},
                'blocks': {
                    'total_8x8_evaluated': 0, 'total_8x8_compensated': 0,
                    'motion_compensation_ratio': 0.0, 'total_2x2_blocks_saved': 0,
                    'average_blocks_saved_per_compensation': 0.0
                },
                'motion_vectors': {'top_vectors': [], 'magnitude_distribution': defaultdict(int)},
                'zones': {'usage_count': defaultdict(int)},
                'merging': {'total_strips': 0, 'blocks_before_merge': 0, 'blocks_after_merge': 0, 'merge_efficiency': 0.0},
                'data_size': {'motion_data_bytes': 0, 'motion_data_ratio': 0.0}
            }
        
        f = motion_stats_dict['frames']
        self.motion_compensation_stats['frames']['total_processed'] += f['total_processed']
        self.motion_compensation_stats['frames']['with_motion_compensation'] += f['with_motion_compensation']
        
        b = motion_stats_dict['blocks']
        self.motion_compensation_stats['blocks']['total_8x8_evaluated'] += b['total_8x8_evaluated']
        self.motion_compensation_stats['blocks']['total_8x8_compensated'] += b['total_8x8_compensated']
        self.motion_compensation_stats['blocks']['total_2x2_blocks_saved'] += b['total_2x2_blocks_saved']
        
        mv = motion_stats_dict['motion_vectors']
        for (dx, dy), count in mv['top_vectors']:
            found = False
            for i, ((edx, edy), ec) in enumerate(self.motion_compensation_stats['motion_vectors']['top_vectors']):
                if edx == dx and edy == dy:
                    self.motion_compensation_stats['motion_vectors']['top_vectors'][i] = ((dx, dy), ec + count)
                    found = True
                    break
            if not found:
                self.motion_compensation_stats['motion_vectors']['top_vectors'].append(((dx, dy), count))
        
        for magnitude, count in mv['magnitude_distribution'].items():
            self.motion_compensation_stats['motion_vectors']['magnitude_distribution'][magnitude] += count
        
        for zone_idx, count in motion_stats_dict['zones']['usage_count'].items():
            self.motion_compensation_stats['zones']['usage_count'][zone_idx] += count
        
        if 'merging' in motion_stats_dict:
            m = motion_stats_dict['merging']
            self.motion_compensation_stats['merging']['total_strips'] += m['total_strips']
            self.motion_compensation_stats['merging']['blocks_before_merge'] += m['blocks_before_merge']
            self.motion_compensation_stats['merging']['blocks_after_merge'] += m['blocks_after_merge']
        
        self.motion_compensation_stats['data_size']['motion_data_bytes'] += motion_stats_dict['data_size']['motion_data_bytes']
    
    def finalize_motion_compensation_stats(self):
        if self.motion_compensation_stats is None:
            return
        
        f = self.motion_compensation_stats['frames']
        if f['total_processed'] > 0:
            f['motion_compensation_frame_ratio'] = f['with_motion_compensation'] / f['total_processed']
        
        b = self.motion_compensation_stats['blocks']
        if b['total_8x8_evaluated'] > 0:
            b['motion_compensation_ratio'] = b['total_8x8_compensated'] / b['total_8x8_evaluated']
        if b['total_8x8_compensated'] > 0:
            b['average_blocks_saved_per_compensation'] = b['total_2x2_blocks_saved'] / b['total_8x8_compensated']
        
        m = self.motion_compensation_stats['merging']
        if m['blocks_before_merge'] > 0:
            m['merge_efficiency'] = (m['blocks_before_merge'] - m['total_strips']) / m['blocks_before_merge']
        
        self.motion_compensation_stats['motion_vectors']['top_vectors'].sort(key=lambda x: x[1], reverse=True)
        self.motion_compensation_stats['motion_vectors']['top_vectors'] = \
            self.motion_compensation_stats['motion_vectors']['top_vectors'][:5]
        
        if self.total_p_frame_bytes > 0:
            self.motion_compensation_stats['data_size']['motion_data_ratio'] = \
                self.motion_compensation_stats['data_size']['motion_data_bytes'] / self.total_p_frame_bytes
