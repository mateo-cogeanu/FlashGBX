# utils/system_utils.py
import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def no_window_flags():
    return 0x08000000 if sys.platform == "win32" else 0
