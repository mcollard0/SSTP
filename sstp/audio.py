import os
import shutil
import subprocess
import threading
from pathlib import Path
from sstp.config import config, DEFAULT_SOUND_PATH, DEFAULT_ALARM_PATH, DEFAULT_CLICK_PATH


class AudioPlayer:
    """Non-blocking audio engine supporting PulseAudio, PipeWire, and ALSA."""

    def __init__(self):
        self.paplay_bin = shutil.which("paplay")
        self.pw_play_bin = shutil.which("pw-play")
        self.aplay_bin = shutil.which("aplay")

    def _play_async(self, filepath: str, volume: float = 1.0):
        if not os.path.exists(filepath):
            print(f"[Audio] Sound file not found: {filepath}")
            return

        def _worker():
            vol_clamped = max(0.0, min(1.0, volume))
            if vol_clamped <= 0.001:
                return

            try:
                if self.paplay_bin:
                    # paplay volume is 0..65536
                    pa_vol = int(vol_clamped * 65536)
                    cmd = [self.paplay_bin, f"--volume={pa_vol}", filepath]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif self.pw_play_bin:
                    cmd = [self.pw_play_bin, f"--volume={vol_clamped:.2f}", filepath]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif self.aplay_bin:
                    cmd = [self.aplay_bin, "-q", filepath]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"[Audio] Playback error: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def play_tick(self):
        if not config.settings.get("sound_enabled", True):
            return
        if not config.settings.get("tick_sound_enabled", True):
            return

        sound_file = config.settings.get("sound_file", DEFAULT_SOUND_PATH)
        volume = config.settings.get("volume", 0.8)
        self._play_async(sound_file, volume)

    def play_alarm(self):
        if not config.settings.get("sound_enabled", True):
            return
        if not config.settings.get("alarm_enabled", True):
            return

        volume = config.settings.get("volume", 0.8)
        self._play_async(DEFAULT_ALARM_PATH, volume)

    def play_click(self):
        # Click sound is subtle tactile feedback for switch interaction
        volume = min(1.0, config.settings.get("volume", 0.8) * 0.9)
        self._play_async(DEFAULT_CLICK_PATH, volume)

    def test_sound(self, filepath: str, volume: float):
        self._play_async(filepath, volume)


audio = AudioPlayer()
