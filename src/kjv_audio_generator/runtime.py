from __future__ import annotations

import sys
from pathlib import Path


def runtime_root() -> Path:
    """Return the app folder in source mode or PyInstaller's bundled-data folder."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parents[2]


def bundled_ffmpeg() -> Path:
    return runtime_root() / "ffmpeg.exe"
