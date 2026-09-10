import json
import os
from datetime import datetime, date
from pathlib import Path

DEFAULT_SOUND_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "tick.wav")
DEFAULT_ALARM_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "alarm.wav")
DEFAULT_CLICK_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "click.wav")

CONFIG_DIR = Path.home() / ".config" / "sstp"
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

    def _update_daily_stats(self):
        today_str = date.today().isoformat()
        last_date = self.stats.get("last_active_date", "")

        if last_date != today_str:
            if last_date:
                try:
                    last_d = date.fromisoformat(last_date)
                    delta = (date.today() - last_d).days
                    if delta > 1:
                        self.stats["daily_streak"] = 0
                except Exception:
                    pass
            self.stats["today_completed"] = 0

    def record_completed_session(self, session_type: str, duration_minutes: int):
        today_str = date.today().isoformat()
        last_date = self.stats.get("last_active_date", "")

        if last_date != today_str:
            if last_date:
                try:
                    last_d = date.fromisoformat(last_date)
                    delta = (date.today() - last_d).days
                    if delta == 1:
                        self.stats["daily_streak"] += 1
                    elif delta > 1:
                        self.stats["daily_streak"] = 1
                except Exception:
                    self.stats["daily_streak"] = 1
            else:
                self.stats["daily_streak"] = 1
            self.stats["last_active_date"] = today_str
            self.stats["today_completed"] = 0

        if session_type == "work":
            self.stats["total_pomodoros_completed"] += 1
            self.stats["total_focus_minutes"] += duration_minutes
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
            "last_active_date": date.today().isoformat(),
            "today_completed": 0,
            "history": [],
        }
        self.save()


config = ConfigManager()
