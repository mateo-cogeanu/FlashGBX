#encoder/video_encoder.py

import argparse
import pathlib
import signal
import shutil
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

_tmp_dir = None


def parse_duration(value):
    if value is None:
        return None
    val = value.strip().lower()
    if val == "full":
        return None
    try:
        duration = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "--duration must be a positive number or 'full'"
        )
    if duration < 0:
        raise argparse.ArgumentTypeError("--duration must be non-negative")
    return duration

def _cleanup_temp():
    global _tmp_dir
    if _tmp_dir and pathlib.Path(_tmp_dir).exists():
        try:
            shutil.rmtree(_tmp_dir, ignore_errors=True)
            print(f"\n🧹 Temp files cleaned up: {_tmp_dir}")
        except Exception:
            pass

def _signal_handler(sig, frame):
    print("\n\n⚠️  Interrupted by user (Ctrl+C)")
    _cleanup_temp()
    sys.exit(0)

from video_encoder_core import VideoEncoderCore
from video_encoder_utils import extract_frames_from_video
from core_encoder import DEFAULT_UNIFIED_CODEBOOK_SIZE, DEFAULT_ENABLED_SEGMENTS_BITMAP, DEFAULT_ENABLED_MEDIUM_SEGMENTS_BITMAP
from motion_compensation import DEFAULT_UPDATE_THRESHOLD

def parse_sample_rate(value):
    if isinstance(value, int):
        return value
    try:
        rate = int(str(value).strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid sample rate: {value!r}. Use an integer between 6500 and 44100.")
    if rate < 6500 or rate > 44100:
        raise argparse.ArgumentTypeError(
            f"Sample rate {rate} out of range. Must be between 6500 and 44100 Hz.")
    return rate

def main():
    global _tmp_dir

    signal.signal(signal.SIGINT, _signal_handler)

    pa = argparse.ArgumentParser(description="Encode to GBA YUV9 with unified codebook")
    pa.add_argument("input")
    pa.add_argument("--duration", type=parse_duration, default=None,
                   help="Seconds to encode, or 'full' to use the entire video. Default: full video")
    pa.add_argument("--start-time", type=float, default=0.0,
                   help="Start time in seconds (default: 0 = beginning of video)")
    pa.add_argument("--fps", type=float, default=None,
                   help="Target FPS — snapped to nearest GBA-native value. "
                        "Default: 9.9546. Max supported: 14.9319.")
    pa.add_argument("--no-letterbox", action="store_true",
                   help="Stretch video to 240×160 instead of letterboxing/pillarboxing")
    pa.add_argument("--crop", type=str, default=None,
                   help="Crop source before scaling: x,y,w,h (pixel coordinates in source resolution)")
    pa.add_argument("--out", default="video/video_data")
    pa.add_argument("--i-frame-interval", type=int, default=60)
    pa.add_argument("--diff-threshold", type=float, default=2.5)
    pa.add_argument("--force-i-threshold", type=float, default=0.7)
    pa.add_argument("--variance-threshold", type=float, default=10,
                   help="Variance threshold for flat vs texture block (default 10.0)")
    pa.add_argument("--color-fallback-threshold", type=float, default=10,
                   help="Color block fallback distance threshold (default 10.0)")
    pa.add_argument("--codebook-size", type=int, default=DEFAULT_UNIFIED_CODEBOOK_SIZE,
                   help=f"Unified codebook size (default {DEFAULT_UNIFIED_CODEBOOK_SIZE})")
    pa.add_argument("--kmeans-max-iter", type=int, default=200)
    pa.add_argument("--threads", type=int, default=None)
    pa.add_argument("--i-frame-weight", type=int, default=3,
                   help="I-frame block weight multiplier in clustering (default 3)")
    pa.add_argument("--max-workers", type=int, default=None,
                   help="Max worker processes for GOP processing (default: CPU count - 1)")
    pa.add_argument("--dither", action="store_true",
                   help="Enable Floyd-Steinberg dithering for better quality")
    pa.add_argument("--enabled-segments-bitmap", type=int, default=DEFAULT_ENABLED_SEGMENTS_BITMAP,
                   help=f"Bitmap of enabled small codebook segments (default 0x{DEFAULT_ENABLED_SEGMENTS_BITMAP:04X})")
    pa.add_argument("--enabled-medium-segments-bitmap", type=int, default=DEFAULT_ENABLED_MEDIUM_SEGMENTS_BITMAP,
                   help=f"Bitmap of enabled medium codebook segments (default 0x{DEFAULT_ENABLED_MEDIUM_SEGMENTS_BITMAP:02X})")
    pa.add_argument("--motion-compensation", action="store_true", default=True,
                   help="Enable motion compensation (default: enabled)")
    pa.add_argument("--no-motion-compensation", action="store_true",
                   help="Disable motion compensation")
    pa.add_argument("--motion-update-threshold", type=int, default=DEFAULT_UPDATE_THRESHOLD,
                   help="Motion compensation update threshold: max 2x2 blocks to update in 8x8 block (default 8)")
    pa.add_argument("--audio-sample-rate", type=parse_sample_rate, default=18157,
                   help="Audio sample rate in Hz (6500-44100). "
                        "PCM: any value in range. "
                        "ADPCM: snapped to nearest nice rate (6689, 10512, 11468, 13379, 18157, 20068, 21024). "
                        "Default: 18157 Hz.")
    pa.add_argument("--audio-format", choices=["pcm", "adpcm"], default="pcm",
                   help="Audio format: 'pcm' (8-bit signed, default) or 'adpcm' "
                        "(IMA ADPCM 4-bit, ~50%% smaller, max 14.9319 fps)")
    pa.add_argument("--no-audio", action="store_true",
                   help="Disable audio extraction")
    pa.add_argument("--audio-only", action="store_true",
                   help="Export audio files only, skip video processing")
    pa.add_argument("--volume", type=float, default=100.0,
                   help="Audio volume percent (100=original, 200=double, 50=half)")
    pa.add_argument("--skip-key", type=int, default=0x0001,
                   help="GBA button bitmask for the skip key (default: 0x0001 = A_BUTTON). "
                        "Pass 0 to disable. Combine buttons with bitwise OR "
                        "(e.g. 0x0009 = A_BUTTON|START_BUTTON).")
    args = pa.parse_args()

    if args.audio_only:
        from audio_encoder import AudioEncoder
        audio_encoder = AudioEncoder(sample_rate=args.audio_sample_rate,
                                     audio_format=args.audio_format)
        full_duration = args.duration is None
        frames, actual_output_fps, mmap_path = extract_frames_from_video(
            args.input, args.duration, args.fps if args.fps else 9.9546, full_duration, args.dither,
            start_time=args.start_time, letterbox=not args.no_letterbox, crop=args.crop,
        )
        frame_count = len(frames)
        audio_duration = frame_count / actual_output_fps
        _audio_result = audio_encoder.extract_audio_from_video(
            args.input, audio_duration, start_time=args.start_time,
            frame_count=frame_count, volume_percent=args.volume,
            temp_dir=str(pathlib.Path(mmap_path).parent) if 'mmap_path' in dir() else None)
        if _audio_result is None:
            print("❌ Audio extraction failed: no audio stream found in video.")
            return
        audio_data, i_frame_audio_offsets, frame_audio_offsets = _audio_result
        output_base = pathlib.Path(args.out)
        output_base.parent.mkdir(parents=True, exist_ok=True)
        include_dir = pathlib.Path(__file__).parent.parent / "include" / "video"
        include_dir.mkdir(parents=True, exist_ok=True)
        audio_header_path = include_dir / "audio_data.h"
        video_fps_raw = int(round(actual_output_fps * 10000))
        frame_audio_offsets = audio_encoder.recalculate_frame_offsets(
            len(frame_audio_offsets), len(audio_data), video_fps_raw)
        audio_encoder.write_audio_header(audio_header_path, audio_data, audio_duration, i_frame_audio_offsets, frame_audio_offsets)
        audio_encoder.write_audio_bin_files(output_base.parent, audio_data, i_frame_audio_offsets, frame_audio_offsets)
        print(f"✓ Audio files generated: {audio_header_path} / audio_data.bin")
        return

    full_duration = args.duration is None
    frames, actual_output_fps, mmap_path = extract_frames_from_video(
        args.input, args.duration, args.fps if args.fps else 9.9546, full_duration, args.dither,
        start_time=args.start_time, letterbox=not args.no_letterbox, crop=args.crop,
    )
    _tmp_dir = str(pathlib.Path(mmap_path).parent)

    if args.fps is not None and args.fps > actual_output_fps:
        print(f"⚠️  Requested FPS ({args.fps:.4f}) > source FPS ({actual_output_fps:.4f}). Using source FPS.")
    used_fps = actual_output_fps

    audio_data = None
    audio_duration = len(frames) / used_fps
    if not args.no_audio:
        from audio_encoder import AudioEncoder
        audio_encoder = AudioEncoder(sample_rate=args.audio_sample_rate,
                                     audio_format=args.audio_format)
        _audio_result = audio_encoder.extract_audio_from_video(
            args.input, audio_duration, start_time=args.start_time,
            frame_count=len(frames), volume_percent=args.volume,
            temp_dir=_tmp_dir)
        if _audio_result is None:
            print("⚠️  Audio extraction failed (no audio stream?), continuing with video only...")
            args.no_audio = True
        else:
            audio_data, i_frame_audio_offsets, frame_audio_offsets = _audio_result

    motion_compensation_enabled = args.motion_compensation and not args.no_motion_compensation

    try:
        encoder = VideoEncoderCore()
        result = encoder.encode_video(
            frames=frames,
            output_path=args.out,
            i_frame_interval=args.i_frame_interval,
            diff_threshold=args.diff_threshold,
            force_i_threshold=args.force_i_threshold,
            variance_threshold=args.variance_threshold,
            color_fallback_threshold=args.color_fallback_threshold,
            codebook_size=args.codebook_size,
            kmeans_max_iter=args.kmeans_max_iter,
            i_frame_weight=args.i_frame_weight,
            max_workers=args.max_workers,
            enabled_segments_bitmap=args.enabled_segments_bitmap,
            enabled_medium_segments_bitmap=args.enabled_medium_segments_bitmap,
            fps=used_fps,
            motion_compensation_enabled=motion_compensation_enabled,
            motion_update_threshold=args.motion_update_threshold
        )

        if len(result) == 3:
            all_data, frame_offsets, i_frame_timestamps = result
        else:
            all_data, frame_offsets = result
            i_frame_timestamps = None

        if audio_data is not None:
            output_base = pathlib.Path(args.out)
            output_base.parent.mkdir(parents=True, exist_ok=True)
            include_dir = pathlib.Path(__file__).parent.parent / "include" / "video"
            include_dir.mkdir(parents=True, exist_ok=True)
            audio_header_path = include_dir / "audio_data.h"
            video_fps_raw = int(round(used_fps * 10000))
            frame_audio_offsets = audio_encoder.recalculate_frame_offsets(
                len(frame_audio_offsets), len(audio_data), video_fps_raw)
            audio_encoder.write_audio_header(audio_header_path, audio_data, audio_duration, i_frame_audio_offsets, frame_audio_offsets)
            audio_encoder.write_audio_bin_files(output_base.parent, audio_data, i_frame_audio_offsets, frame_audio_offsets)
            print(f"✓ Audio files generated: {audio_header_path} / audio_data.bin")

        from video_encoder_utils import copy_decoproject_output
        project_root  = pathlib.Path(__file__).parent.parent
        video_bin_dir = pathlib.Path(args.out).parent
        audio_fmt     = args.audio_format if not args.no_audio else "pcm"
        _spf    = int(getattr(audio_encoder, 'samples_per_frame', 0)) if audio_data else 0
        _reload = int(getattr(audio_encoder, 'timer_reload',      0)) if audio_data else 0
        _sr     = getattr(audio_encoder, 'real_sample_rate', args.audio_sample_rate) if audio_data else args.audio_sample_rate
        _dur_ms = int(audio_duration * 1000) if audio_data else 0
        _alen   = len(audio_data) if audio_data else 0
        _fcnt   = len(frame_audio_offsets) if (audio_data and frame_audio_offsets) else 0
        _inc    = pathlib.Path(__file__).parent.parent / "include" / "video"
        copy_decoproject_output(
            project_root       = project_root,
            video_bin_dir      = video_bin_dir,
            include_video_dir  = _inc,
            audio_format       = audio_fmt,
            frame_cnt          = len(frame_offsets),
            total_bytes        = len(all_data),
            codebook_size      = args.codebook_size,
            output_fps         = used_fps,
            sample_rate        = int(_sr),
            adpcm_timer_reload = _reload,
            adpcm_spf          = _spf,
            audio_duration_ms  = _dur_ms,
            audio_data_len     = _alen,
            frame_audio_count  = _fcnt,
            skip_key           = args.skip_key,
            no_audio           = args.no_audio,
        )

    except KeyboardInterrupt:
        del frames
        _cleanup_temp()

if __name__ == "__main__":
    main()
