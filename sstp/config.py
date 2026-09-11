import json
import os
from datetime import datetime, date
from pathlib import Path

import sys

DEFAULT_SOUND_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "tick.wav")
DEFAULT_ALARM_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "alarm.wav")
DEFAULT_CLICK_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "click.wav")


def get_config_dir() -> Path:
    """Returns platform-standard configuration directory."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "sstp"
        return Path.home() / "AppData" / "Roaming" / "sstp"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "sstp"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / "sstp"
        return Path.home() / ".config" / "sstp"


CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    """Manages application settings and persistent Pomodoro statistics."""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.settings = {
            "work_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
            "short_break_enabled": True,
            "long_break_enabled": True,
            "sound_enabled": True,
            "sound_file": DEFAULT_SOUND_PATH,
            "volume": 0.8,
            "alarm_enabled": True,
            "tick_sound_enabled": True,
            "frameless_mode": True,
            "tube_glow_enabled": True,
            "scale": 0.5,
        }

        self.stats = {
            "total_pomodoros_completed": 0,
            "total_short_breaks_completed": 0,
            "total_long_breaks_completed": 0,
            "total_focus_minutes": 0,
            "daily_streak": 0,
            "last_active_date": "",
            "today_completed": 0,
            "history": [],
        }

        self.load()

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "settings" in data:
                        self.settings.update(data["settings"])
                    if "stats" in data:
                        self.stats.update(data["stats"])
                self._update_daily_stats()
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"settings": self.settings, "stats": self.stats}, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get_sound_file(self) -> str:
        sound = self.settings.get("sound_file", DEFAULT_SOUND_PATH)
        if not sound or not os.path.exists(sound):
            return DEFAULT_SOUND_PATH
        return sound

    def _update_daily_stats(self):
        today_str = date.today().isoformat()
        last_date = self.stats.get("last_active_date", "")

        changed = False
        if last_date != today_str:
            if last_date:
                try:
                    last_d = date.fromisoformat(last_date)
                    delta = (date.today() - last_d).days
                    if delta > 1:
                        if self.stats.get("daily_streak", 0) != 0:
                            self.stats["daily_streak"] = 0
                            changed = True
                except Exception:
                    pass
            if self.stats.get("today_completed", 0) != 0:
                self.stats["today_completed"] = 0
                changed = True

        if changed:
            self.save()

    def record_completed_session(self, session_type: str, duration_minutes: int):
        today_str = date.today().isoformat()
        last_date = self.stats.get("last_active_date", "")

        if session_type == "work":
            self.stats["total_pomodoros_completed"] += 1
            self.stats["total_focus_minutes"] += duration_minutes

            if last_date != today_str:
                self.stats["today_completed"] = 1
                if last_date:
                    try:
                        last_d = date.fromisoformat(last_date)
                        delta = (date.today() - last_d).days
                        if delta == 1:
                            self.stats["daily_streak"] += 1
                        else:
                            self.stats["daily_streak"] = 1
                    except Exception:
                        self.stats["daily_streak"] = 1
                else:
                    self.stats["daily_streak"] = 1
                self.stats["last_active_date"] = today_str
            else:
                self.stats["today_completed"] += 1
        elif session_type == "short_break":
            self.stats["total_short_breaks_completed"] += 1
        elif session_type == "long_break":
            self.stats["total_long_breaks_completed"] += 1

        self.stats["history"].append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "type": session_type,
            "duration": duration_minutes,
        })
        # Keep last 200 records
        if len(self.stats["history"]) > 200:
            self.stats["history"] = self.stats["history"][-200:]

        self.save()

    def reset_statistics(self):
        self.stats = {
            "total_pomodoros_completed": 0,
            "total_short_breaks_completed": 0,
            "total_long_breaks_completed": 0,
            "total_focus_minutes": 0,
            "daily_streak": 0,
            "last_active_date": "",
            "today_completed": 0,
            "history": [],
        }
        self.save()


config = ConfigManager()
