"""Constants and resource path definitions for Stuart Saves the Pomodoro (SSTP)."""

import os
import sys
from pathlib import Path

# Application Version Constant
VERSION = "0.0.1"
__version__ = VERSION


def get_base_dir() -> Path:
    """Returns the base application directory.

    Handles PyInstaller frozen environments (sys._MEIPASS) as well as
    standard source tree execution.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "assets"
OUTPUTS_DIR = BASE_DIR / "outputs"

MACHINE_IMG_PATH = str(OUTPUTS_DIR / "machine.png")
ICON_PATH = str(ASSETS_DIR / "icon.png")
DEFAULT_SOUND_PATH = str(ASSETS_DIR / "sounds" / "tick.wav")
DEFAULT_ALARM_PATH = str(ASSETS_DIR / "sounds" / "alarm.wav")
DEFAULT_CLICK_PATH = str(ASSETS_DIR / "sounds" / "click.wav")
