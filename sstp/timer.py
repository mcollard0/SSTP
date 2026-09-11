import time
from enum import Enum
from typing import Callable, Optional
from sstp.config import config


class TimerState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class SessionType(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class PomodoroTimer:
    """Core Pomodoro timing logic and state machine."""

    def __init__(self):
        self.state = TimerState.IDLE
        self.session_type = SessionType.WORK
        self.pomodoro_count = 0  # Number of completed work sessions in current cycle

        self.total_seconds = self._get_duration_for(self.session_type)
        self.remaining_seconds = self.total_seconds
        self.target_end_time: Optional[float] = None

        # Callbacks
        self.on_tick: Optional[Callable[[int, int], None]] = None
        self.on_state_changed: Optional[Callable[[TimerState], None]] = None
        self.on_session_completed: Optional[Callable[[SessionType, int], None]] = None

    def _get_duration_for(self, session_type: SessionType) -> int:
        settings = config.settings
        if session_type == SessionType.WORK:
            return max(1, int(settings.get("work_minutes", 25))) * 60
        elif session_type == SessionType.SHORT_BREAK:
            return max(1, int(settings.get("short_break_minutes", 5))) * 60
        elif session_type == SessionType.LONG_BREAK:
            return max(1, int(settings.get("long_break_minutes", 15))) * 60
        return 25 * 60

    def refresh_durations( self ):
        """Called when settings are updated to apply new times if idle."""
        short_enabled = config.settings.get( "short_break_enabled", True );
        long_enabled = config.settings.get( "long_break_enabled", True );

        if self.state == TimerState.IDLE:
            if self.session_type == SessionType.SHORT_BREAK and not short_enabled:
                self.session_type = SessionType.WORK;
            elif self.session_type == SessionType.LONG_BREAK and not long_enabled:
                self.session_type = SessionType.WORK;

            self.total_seconds = self._get_duration_for( self.session_type );
            self.remaining_seconds = self.total_seconds;
            if self.on_tick:
                self.on_tick( self.remaining_seconds, self.total_seconds );

    def toggle(self):
        """Action for red button: stops / starts / restarts timer."""
        if self.state == TimerState.IDLE:
            self.start()
        elif self.state == TimerState.RUNNING:
            self.pause()
        elif self.state == TimerState.PAUSED:
            self.resume()
        elif self.state == TimerState.COMPLETED:
            self.restart()

    def start(self):
        if self.state == TimerState.IDLE or self.state == TimerState.COMPLETED:
            self.total_seconds = self._get_duration_for(self.session_type)
            self.remaining_seconds = self.total_seconds
        self.target_end_time = time.monotonic() + self.remaining_seconds
        self.state = TimerState.RUNNING
        if self.on_state_changed:
            self.on_state_changed(self.state)

    def pause(self):
        if self.state == TimerState.RUNNING:
            if self.target_end_time is not None:
                self.remaining_seconds = max(0, int(round(self.target_end_time - time.monotonic())))
                self.target_end_time = None
            self.state = TimerState.PAUSED
            if self.on_state_changed:
                self.on_state_changed(self.state)

    def resume(self):
        if self.state == TimerState.PAUSED:
            self.target_end_time = time.monotonic() + self.remaining_seconds
            self.state = TimerState.RUNNING
            if self.on_state_changed:
                self.on_state_changed(self.state)

    def restart(self):
        self.total_seconds = self._get_duration_for(self.session_type)
        self.remaining_seconds = self.total_seconds
        self.target_end_time = time.monotonic() + self.remaining_seconds
        self.state = TimerState.RUNNING
        if self.on_state_changed:
            self.on_state_changed(self.state)
        if self.on_tick:
            self.on_tick(self.remaining_seconds, self.total_seconds)

    def reset(self):
        self.state = TimerState.IDLE
        self.target_end_time = None
        self.total_seconds = self._get_duration_for(self.session_type)
        self.remaining_seconds = self.total_seconds
        if self.on_state_changed:
            self.on_state_changed(self.state)
        if self.on_tick:
            self.on_tick(self.remaining_seconds, self.total_seconds)

    def advance_to_next_session( self ):
        """Transitions Work -> Short Break -> Work -> ... -> Long Break taking enabled checkboxes into account."""
        short_enabled = config.settings.get( "short_break_enabled", True );
        long_enabled = config.settings.get( "long_break_enabled", True );

        if self.session_type == SessionType.WORK:
            self.pomodoro_count += 1;
            interval = max( 1, int( config.settings.get( "long_break_interval", 4 ) ) );
            is_long_turn = ( self.pomodoro_count % interval == 0 );

            if is_long_turn and long_enabled:
                self.session_type = SessionType.LONG_BREAK;
            elif ( not is_long_turn or not long_enabled ) and short_enabled:
                self.session_type = SessionType.SHORT_BREAK;
            else:
                self.session_type = SessionType.WORK;
        else:
            self.session_type = SessionType.WORK;

        self.state = TimerState.IDLE;
        self.target_end_time = None;
        self.total_seconds = self._get_duration_for( self.session_type );
        self.remaining_seconds = self.total_seconds;

        if self.on_state_changed:
            self.on_state_changed( self.state );
        if self.on_tick:
            self.on_tick( self.remaining_seconds, self.total_seconds );

    def set_session_type(self, new_type: SessionType):
        self.session_type = new_type
        self.reset()

    def tick(self) -> bool:
        """Decrements timer by 1 second if running. Returns True if tick processed."""
        if self.state != TimerState.RUNNING:
            return False

        if self.target_end_time is not None:
            now = time.monotonic()
            expected_remaining = int(round(self.target_end_time - now))
            if expected_remaining < self.remaining_seconds:
                self.remaining_seconds = max(0, expected_remaining)
            else:
                self.remaining_seconds = max(0, self.remaining_seconds - 1)
        elif self.remaining_seconds > 0:
            self.remaining_seconds -= 1

        if self.on_tick:
            self.on_tick(self.remaining_seconds, self.total_seconds)

        if self.remaining_seconds <= 0:
            self.state = TimerState.COMPLETED
            self.target_end_time = None
            duration_mins = max(1, self.total_seconds // 60)
            config.record_completed_session(self.session_type.value, duration_mins)
            if self.on_state_changed:
                self.on_state_changed(self.state)
            if self.on_session_completed:
                self.on_session_completed(self.session_type, duration_mins)
            return False

        return True

    @property
    def formatted_digits(self) -> str:
        """Returns 4-character string of MMSS (e.g. '2500' or '0459')."""
        valid_rem = max(0, self.remaining_seconds)
        mins = min(99, valid_rem // 60)
        secs = min(59, valid_rem % 60)
        return f"{mins:02d}{secs:02d}"

    @property
    def formatted_display(self) -> str:
        """Returns string for tooltips/menus e.g. '25:00'."""
        valid_rem = max(0, self.remaining_seconds)
        mins = valid_rem // 60
        secs = valid_rem % 60
        return f"{mins:02d}:{secs:02d}"
