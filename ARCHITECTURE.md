ARCHITECTURE.md

Stuart Saves the Pomodoro

Using asset: https://michaelcollard.pro/tmp/stuart_fails_to_save_the_universe/assets/trope1_machine.jpg

Use Nano Banana to crop/mask the machine in this image ( in beige ) and save result as /outputs/machine.png. Also recommend you to modify LED to so it shows no numbers.

From this asset, create a Pomodoro timer desktop app for Linux. 

Pressing in the circle area around red button stops/starts/restarts timer. 
Pressing any white button (lower left) opens settings dialog with: 
1. Working time in minutes
5. Sound toggle
6. Sound file selector (ship with a basic digitial clock ticking sound)
7. Sound volume slider
8. Reset statistics button 

Maintain statistics such as number of timers finished, et c. 

Come up with any additional ideas you have. It should also have system tray integration (using GTK+)

Ensure the time shows in the LED panel power left in bright red. The overlay has to be perfect to write over the existing "unlit" segments.

## Configuration & Storage Schema (`~/.config/sstp/config.json`)
- `settings`:
  - `work_minutes` (int, default 25): Focus session duration.
  - `short_break_minutes` (int, default 5): Short break duration.
  - `short_break_enabled` (bool, default True): Toggle checkbox to enable/disable short breaks.
  - `long_break_minutes` (int, default 15): Long break duration.
  - `long_break_enabled` (bool, default True): Toggle checkbox to enable/disable long breaks.
  - `long_break_interval` (int, default 4): Number of focus sessions before a long break cycle.
  - `sound_enabled` (bool, default True): Master toggle for all application sound effects.
  - `sound_file` (str): Filesystem path to selected ticking audio asset.
  - `volume` (float, 0.0-1.0): Sound output volume.
  - `tick_sound_enabled` (bool, default True): Toggle mechanical/digital tick every second.
  - `tube_glow_enabled` (bool, default True): Toggle vacuum tube pulse animation.
  - `scale` (float, 0.3-1.5): Window scaling multiplier for the retro machine form.
- `stats`:
  - `total_pomodoros_completed` (int): Lifetime completed work sessions.
  - `total_short_breaks_completed` (int): Lifetime completed short breaks.
  - `total_long_breaks_completed` (int): Lifetime completed long breaks.
  - `total_focus_minutes` (int): Cumulative minutes of completed focus time.
  - `daily_streak` (int): Consecutive days with completed pomodoros.
  - `last_active_date` (str, ISO-8601): Date string of last active session.
  - `today_completed` (int): Number of work sessions finished today.
  - `history` (list of dicts): Rolling log of recent sessions (timestamp, type, duration).

## Interfaces & API Endpoints
- **Desktop System Tray**: Status icon with popup menu (Start/Pause, Skip to Next, Reset, Settings & Stats, Show/Hide, Quit).
- **Desktop Notifications**: libnotify / `Notify.Notification` with automatic fallback to `notify-send`.
- **Keyboard Shortcuts**: Space (toggle), 's' (settings), 'r' (reset), Esc (minimize to tray), 'q' (quit).

## Key Business Logic Rules
- **Cycle Transitions**: Work -> Short Break -> Work -> ... -> Long Break (at interval).
  - If Short Break is disabled, intermediate breaks are skipped and the timer proceeds directly to the next Work session.
  - If Long Break is disabled, interval cycles fall back to Short Break if enabled, or advance to Work.
  - If both breaks are disabled, sessions loop continuously in Work mode.
- **Form Opacity & Transparency**:
  - Regular Form (`PomodoroMachineApp`): 100% opaque retro machine rendering on a transparent desktop canvas.
  - Settings Form (`SettingsDialog`): Translucency reduced to 25% transparency (75% opacity) with a styled dark backing plate.

## Current Feature Status
- Main machine UI with circular red rotary dial, LED seven-segment chronometer, vacuum tube glow animation, and tactile audio.
- Settings & Statistics dialog with 75% opacity and checkboxes to turn Short Break and Long Break on and off.
- System tray integration and background persistence.

## Known Issues / Constraints
- Requires a compositing window manager / Wayland compositor for window-level alpha transparency.

