# main.py
# Modified for FlashGBX on 2026-07-18: cross-platform devkitARM discovery.
import sys
import subprocess
import os
import time
import argparse
import signal
import shutil
import multiprocessing
from pathlib import Path

def _no_window():
    return 0x08000000 if sys.platform == "win32" else 0

if getattr(sys, 'frozen', False):
    multiprocessing.freeze_support()

if sys.platform == "win32":
    try:
        import multiprocessing.popen_spawn_win32 as _psw
        import _winapi as _wapi
        import msvcrt as _msvcrt
        import os as _os
        from multiprocessing import spawn as _spawn, util as _util, reduction as _red
        from multiprocessing.popen_spawn_win32 import (
            WINENV as _WINENV, _path_eq, set_spawning_popen, _close_handles
        )
        _CREATE_NO_WINDOW = 0x08000000
        _orig_Popen = _psw.Popen

        class _NoWindowPopen(_orig_Popen):
            def __init__(self, process_obj):
                prep_data = _spawn.get_preparation_data(process_obj._name)
                rhandle, whandle = _wapi.CreatePipe(None, 0)
                wfd = _msvcrt.open_osfhandle(whandle, 0)
                cmd = _spawn.get_command_line(parent_pid=_os.getpid(),
                                              pipe_handle=rhandle)
                python_exe = _spawn.get_executable()
                if _WINENV and _path_eq(python_exe, sys.executable):
                    cmd[0] = python_exe = sys._base_executable
                    env = _os.environ.copy()
                    env["__PYVENV_LAUNCHER__"] = sys.executable
                else:
                    env = None
                cmd = ' '.join('"%s"' % x for x in cmd)
                import subprocess as _sp
                _si = _sp.STARTUPINFO()
                _si.dwFlags = _wapi.STARTF_USESHOWWINDOW
                _si.wShowWindow = 0
                with open(wfd, 'wb', closefd=True) as to_child:
                    try:
                        hp, ht, pid, tid = _wapi.CreateProcess(
                            python_exe, cmd,
                            None, None, False, _CREATE_NO_WINDOW, env, None, _si)
                        _wapi.CloseHandle(ht)
                    except:
                        _wapi.CloseHandle(rhandle)
                        raise
                    self.pid = pid
                    self.returncode = None
                    self._handle = hp
                    self.sentinel = int(hp)
                    self.finalizer = _util.Finalize(self, _close_handles,
                                                    (self.sentinel, int(rhandle)))
                    set_spawning_popen(self)
                    try:
                        _red.dump(prep_data, to_child)
                        _red.dump(process_obj, to_child)
                    finally:
                        set_spawning_popen(None)

        _psw.Popen = _NoWindowPopen
    except Exception:
        pass

_encoder_proc = None


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

def _signal_handler(sig, frame):
    global _encoder_proc
    print("\n\n⚠️  Interrupted by user (Ctrl+C)")
    if _encoder_proc and _encoder_proc.poll() is None:
        _encoder_proc.terminate()
        try:
            _encoder_proc.wait(timeout=5)
        except Exception:
            _encoder_proc.kill()
    root = Path(__file__).parent
    for d in ("temp", "video", "build"):
        p = root / d
        if p.exists():
            shutil.rmtree(str(p), ignore_errors=True)
    print("🧹 Temp files cleaned up")
    sys.exit(0)

def ensure_requirements():
    try:
        import cv2
        import numpy
        import numba
        import scipy
        import sklearn
        from pydub import AudioSegment
        print("✓ All Python dependencies are installed.")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)

def _find_devkitarm():
    """Locate devkitARM on Windows, macOS, or Linux.

    Modified for the FlashGBX integration: upstream's direct-make path used
    Windows paths on every platform, which prevented ROM exports on macOS and
    Linux.
    """
    configured = os.environ.get("DEVKITARM", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.extend([
        Path("C:/devkitPro/devkitARM"),
        Path("/opt/devkitpro/devkitARM"),
        Path("/opt/devkitPro/devkitARM"),
    ])
    gcc = shutil.which("arm-none-eabi-gcc")
    if gcc:
        candidates.insert(0, Path(gcc).resolve().parent.parent)
    for candidate in candidates:
        executable = candidate / "bin" / (
            "arm-none-eabi-gcc.exe" if sys.platform == "win32" else "arm-none-eabi-gcc"
        )
        if executable.is_file() and (candidate / "gba_rules").is_file():
            return candidate
    return None


def check_devkitpro(silent=False):
    devkitarm = _find_devkitarm()
    if devkitarm is not None:
        if not silent:
            print(f"✓ devkitPro toolchain found at {devkitarm}")
        return True
    if not silent:
        print("❌ devkitPro not found. Please install devkitPro with libgba.")
        print("Visit: https://devkitpro.org/wiki/Getting_Started")
    return False


def build_gba(silent=False):
    if not silent:
        print("Building GBA ROM...")
    if getattr(sys, 'frozen', False):
        project_dir_path = Path(sys.executable).resolve().parent
    else:
        project_dir_path = Path(__file__).resolve().parent

    build_dir = project_dir_path
    _tmp_dir = None

    if sys.platform == "win32" and " " in str(project_dir_path):
        import tempfile, shutil
        _tmp_dir = Path("C:/GBAVideoBuild")
        if _tmp_dir.exists():
            shutil.rmtree(str(_tmp_dir), ignore_errors=True)
        for sub in ("src", "include", "video", "libagbsyscall", "Makefile"):
            src = project_dir_path / sub
            dst = _tmp_dir / sub
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            elif src.is_file():
                _tmp_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
        build_dir = _tmp_dir

    project_dir = str(build_dir).replace("\\", "/")
    msys2_shell = Path("C:/devkitPro/msys2/msys2_shell.cmd")

    try:
        if msys2_shell.exists():
            make_cmd = (
                "export DEVKITPRO=/opt/devkitpro && "
                "export DEVKITARM=/opt/devkitpro/devkitARM && "
                "cd \"$GBA_PROJECT_DIR\" && "
                "make"
            )
            cmd = [str(msys2_shell), "-defterm", "-no-start", "-mingw32", "-c", make_cmd]
            env = os.environ.copy()
            env["GBA_PROJECT_DIR"] = project_dir
        else:
            devkitarm = _find_devkitarm()
            if devkitarm is None:
                return False, "devkitPro with the gba-dev tools was not found."
            if not silent:
                print(f"  (building with devkitARM at {devkitarm})")
            env = os.environ.copy()
            env["DEVKITARM"] = str(devkitarm)
            env.setdefault("DEVKITPRO", str(devkitarm.parent))
            env["PATH"] = str(devkitarm / "bin") + os.pathsep + env.get("PATH", "")
            cmd = ["make"]

        result = subprocess.run(cmd, check=True, text=True, capture_output=True,
                               cwd=str(build_dir),
                               env=env,
                               creationflags=_no_window())
        if not silent:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("Build warnings:", result.stderr)
        gba_path = project_dir_path / "GBA_Video.gba"
        gba_built = build_dir / "GBA_Video.gba"
        if _tmp_dir and gba_built.exists():
            import shutil
            shutil.copy2(str(gba_built), str(gba_path))
        if gba_path.exists():
            if not silent:
                print(f"✓ GBA ROM created: {gba_path.name}")
            return True, ""
        msg = "No .gba file generated."
        if not silent:
            print(f"❌ {msg}")
        return False, msg
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e))[-800:]
        if not silent:
            print(f"❌ Build failed:\n{msg}")
        return False, msg
    except Exception as e:
        if not silent:
            print(f"❌ Build failed: {e}")
        return False, str(e)
    finally:
        if _tmp_dir and _tmp_dir.exists():
            import shutil
            shutil.rmtree(str(_tmp_dir), ignore_errors=True)


def encode_video(input_path, output_base="video/video_data", silent=False, cancel_event=None, **kwargs):
    encoder_path = Path(__file__).parent / "encoder" / "video_encoder.py"
    if not encoder_path.exists():
        print(f"❌ Encoder not found at {encoder_path}")
        return False
    
    cmd = [sys.executable, str(encoder_path), str(input_path)]
    
    if kwargs.get("fps") is not None:
        cmd.extend(["--fps", str(kwargs["fps"])])
    if kwargs.get("duration") is not None:
        cmd.extend(["--duration", str(kwargs["duration"])])
    if kwargs.get("i_frame_interval"):
        cmd.extend(["--i-frame-interval", str(kwargs["i_frame_interval"])])
    if kwargs.get("audio_sample_rate") is not None:
        cmd.extend(["--audio-sample-rate", str(kwargs["audio_sample_rate"])])
    if kwargs.get("audio_format"):
        cmd.extend(["--audio-format", str(kwargs["audio_format"])])
    if kwargs.get("no_audio"):
        cmd.append("--no-audio")
    if kwargs.get("dither", True):
        cmd.append("--dither")
    if kwargs.get("max_workers"):
        cmd.extend(["--max-workers", str(kwargs["max_workers"])])
    if kwargs.get("diff_threshold") is not None:
        cmd.extend(["--diff-threshold", str(kwargs["diff_threshold"])])
    if kwargs.get("variance_threshold") is not None:
        cmd.extend(["--variance-threshold", str(kwargs["variance_threshold"])])
    if kwargs.get("no_motion_compensation"):
        cmd.append("--no-motion-compensation")
    if kwargs.get("motion_update_threshold") is not None:
        cmd.extend(["--motion-update-threshold", str(kwargs["motion_update_threshold"])])
    if kwargs.get("color_fallback_threshold") is not None:
        cmd.extend(["--color-fallback-threshold", str(kwargs["color_fallback_threshold"])])
    if kwargs.get("codebook_size") is not None:
        cmd.extend(["--codebook-size", str(kwargs["codebook_size"])])
    if kwargs.get("kmeans_max_iter") is not None:
        cmd.extend(["--kmeans-max-iter", str(kwargs["kmeans_max_iter"])])
    if kwargs.get("i_frame_weight") is not None:
        cmd.extend(["--i-frame-weight", str(kwargs["i_frame_weight"])])
    if kwargs.get("enabled_segments_bitmap") is not None:
        cmd.extend(["--enabled-segments-bitmap", str(kwargs["enabled_segments_bitmap"])])
    if kwargs.get("enabled_medium_segments_bitmap") is not None:
        cmd.extend(["--enabled-medium-segments-bitmap", str(kwargs["enabled_medium_segments_bitmap"])])
    if kwargs.get("force_i_threshold") is not None:
        cmd.extend(["--force-i-threshold", str(kwargs["force_i_threshold"])])
    if kwargs.get("volume") is not None:
        cmd.extend(["--volume", str(kwargs["volume"])])

    cmd.append("--out")
    cmd.append(str(output_base))

    if not silent:
        print(f"Running encoder: {' '.join(cmd)}")
    try:
        global _encoder_proc
        stdout = subprocess.DEVNULL if silent else None
        stderr = subprocess.DEVNULL if silent else None
        flags = _no_window() if getattr(sys, 'frozen', False) else 0
        _encoder_proc = subprocess.Popen(
            cmd,
            stdout=stdout,
            stderr=stderr,
            encoding='utf-8' if not silent else None,
            creationflags=flags,
        )
        
        while _encoder_proc.poll() is None:
            if cancel_event and cancel_event.is_set():
                _encoder_proc.terminate()
                try:
                    _encoder_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    _encoder_proc.kill()
                return False
            time.sleep(0.1)

        if _encoder_proc.returncode != 0:
            print(f"❌ Encoder failed with exit code {_encoder_proc.returncode}")
            return False
        _encoder_proc = None
        return True
    except KeyboardInterrupt:
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Encoder failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Encoder error: {e}")
        return False

def _run_encoder_subprocess():
    sys.argv.remove("--run-encoder")

    if sys.platform == "win32":
        import subprocess as _sp
        _orig = _sp.Popen
        class _NoConsolePopen(_orig):
            def __init__(self, *args, **kwargs):
                kwargs["creationflags"] = kwargs.get("creationflags", 0) | 0x08000000
                super().__init__(*args, **kwargs)
        _sp.Popen = _NoConsolePopen

    base_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    encoder_dir = base_dir / "encoder"
    if str(encoder_dir) not in sys.path:
        sys.path.insert(0, str(encoder_dir))
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    import video_encoder
    video_encoder.main()


def main():
    if "--run-encoder" in sys.argv:
        _run_encoder_subprocess()
        return

    signal.signal(signal.SIGINT, _signal_handler)
    parser = argparse.ArgumentParser(
        description="Convert video to GBA ROM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Default behavior: encode full video at source FPS with dithering and 11025 Hz audio."
    )
    parser.add_argument("input", nargs="?", default=None,
                       help="Input video file (MP4, AVI, etc.). Omit to launch the GUI.")
    parser.add_argument("--gui", action="store_true",
                       help="Launch the graphical interface")
    parser.add_argument("--duration", type=parse_duration, default=None,
                       help="Seconds to encode, or 'full' to use the entire video. Default: full video")
    parser.add_argument("--fps", type=float, default=None,
                       help="Target FPS — snapped to nearest supported GBA-native value "
                            "(5.9727, 6.6364, 7.4659, 8.5325, 9.9546, 11.9455, 14.9319). "
                            "Default: 11.9455 fps. Max: 14.9319.")
    parser.add_argument("--i-frame-interval", type=int, default=60,
                       help="Frames between I-frames (default: 60)")
    parser.add_argument("--audio-sample-rate", type=str, default="11025",
                       help="Audio sample rate. Use numbers like 11025, 18157, 22050, 44100, "
                            "or shortcuts: 11k, 18k, 22k, 44k. Default: 11025 (11k)")
    parser.add_argument("--audio-format", choices=["pcm", "adpcm"], default="pcm",
                       help="Audio format: 'pcm' (8-bit signed, default) or 'adpcm' "
                            "(IMA ADPCM 4-bit, ~50%% smaller)")
    parser.add_argument("--no-audio", action="store_true",
                       help="Skip audio encoding")
    parser.add_argument("--no-dither", action="store_true",
                       help="Disable Floyd-Steinberg dithering (dithering is on by default)")
    parser.add_argument("--skip-build", action="store_true",
                       help="Only encode video, don't build ROM")
    parser.add_argument("--output", default="video/video_data",
                       help="Base name for output files (default: video/video_data)")
    parser.add_argument("--max-workers", type=int, default=None,
                       help="Max parallel worker processes (default: CPU count - 1). "
                            "Reduce if you run out of memory.")
    parser.add_argument("--diff-threshold", type=float, default=2.5,
                       help="Threshold for detecting changed 2x2 blocks (default: 2.5)")
    parser.add_argument("--variance-threshold", type=float, default=10.0,
                       help="Variance threshold for flat vs texture block (default: 10.0)")
    parser.add_argument("--no-motion-compensation", action="store_true",
                       help="Disable motion compensation (enabled by default)")
    parser.add_argument("--motion-update-threshold", type=int, default=6,
                       help="Max 2x2 sub-blocks to update inside an 8x8 MC candidate block (0-16, default: 6)")
    parser.add_argument("--color-fallback-threshold", type=float, default=10.0,
                       help="Color block fallback distance threshold (default: 10.0)")
    parser.add_argument("--codebook-size", type=int, default=256,
                       help="Unified codebook size (default: 256)")
    parser.add_argument("--kmeans-max-iter", type=int, default=200,
                       help="K-means max iterations (default: 200)")
    parser.add_argument("--i-frame-weight", type=int, default=3,
                       help="I-frame block weight multiplier in clustering (default: 3)")
    parser.add_argument("--enabled-segments-bitmap", type=int, default=0xFFFF,
                       help="Bitmap of enabled small codebook segments (default: 0xFFFF)")
    parser.add_argument("--enabled-medium-segments-bitmap", type=int, default=0x0F,
                       help="Bitmap of enabled medium codebook segments (default: 0x0F)")
    parser.add_argument("--force-i-threshold", type=float, default=0.7,
                       help="Force I-frame when updated block ratio exceeds this (default: 0.7)")
    parser.add_argument("--volume", type=float, default=100.0,
                       help="Audio volume percent (default: 100)")
    
    args = parser.parse_args()

    if args.gui or args.input is None:
        import ui.main as _ui_main
        sys.exit(_ui_main.main())

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)
    
    print(f"GBA Video Studio")
    print(f"Input: {input_path.name}")
    print(f"Output base: {args.output}")
    print("-" * 50)
    
    ensure_requirements()
    
    print("\n[1/3] Encoding video...")
    encode_args = {
        "duration": args.duration,
        "fps": args.fps,
        "i_frame_interval": args.i_frame_interval,
        "audio_sample_rate": args.audio_sample_rate,
        "audio_format": args.audio_format,
        "no_audio": args.no_audio,
        "dither": not args.no_dither,
        "max_workers": args.max_workers,
        "diff_threshold": args.diff_threshold,
        "variance_threshold": args.variance_threshold,
        "no_motion_compensation": args.no_motion_compensation,
        "motion_update_threshold": args.motion_update_threshold,
        "color_fallback_threshold": args.color_fallback_threshold,
        "codebook_size": args.codebook_size,
        "kmeans_max_iter": args.kmeans_max_iter,
        "i_frame_weight": args.i_frame_weight,
        "enabled_segments_bitmap": args.enabled_segments_bitmap,
        "enabled_medium_segments_bitmap": args.enabled_medium_segments_bitmap,
        "force_i_threshold": args.force_i_threshold,
        "volume": args.volume,
    }
    
    if not encode_video(input_path, args.output, **encode_args):
        sys.exit(1)
    
    if not args.skip_build:
        print("\n[2/3] Checking build environment...")
        if not check_devkitpro():
            print("⚠️  Skipping ROM build. Install devkitPro to compile.")
            sys.exit(0)
        
        print("\n[3/3] Building GBA ROM...")
        ok, err = build_gba()
        if not ok:
            if err:
                print(f"❌ Build error: {err}")
            sys.exit(1)
    
    print("\n✅ Done!")
    if not args.skip_build:
        print("The .gba file is ready to run on a GBA emulator or flash cartridge.")

    root = Path(__file__).parent
    for d in ("temp", "video", "build"):
        p = root / d
        if p.exists():
            shutil.rmtree(str(p), ignore_errors=True)
    print("🧹 Intermediate files cleaned up")

if __name__ == "__main__":
    main()
