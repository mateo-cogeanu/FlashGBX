# encoder/ffmpeg_utils.py
import shutil

_ffmpeg_exe = None


def get_ffmpeg():
    global _ffmpeg_exe
    if _ffmpeg_exe is not None:
        return _ffmpeg_exe

    try:
        import imageio_ffmpeg
        _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        return _ffmpeg_exe
    except Exception:
        pass

    _ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    return _ffmpeg_exe
