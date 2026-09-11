import unittest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from sstp.timer import PomodoroTimer, TimerState, SessionType
from sstp.config import config, ConfigManager, DEFAULT_SOUND_PATH
from sstp.led_renderer import get_digit_segments, DIGIT_MAP, DIGIT_CENTERS, DIGIT_CY


class TestTimer(unittest.TestCase):
    def setUp(self):
        config.settings["work_minutes"] = 25
        config.settings["short_break_minutes"] = 5
        config.settings["long_break_minutes"] = 15
        config.settings["short_break_enabled"] = True
        config.settings["long_break_enabled"] = True
        self.timer = PomodoroTimer()

    def test_initial_state(self):
        self.assertEqual(self.timer.state, TimerState.IDLE)
        self.assertEqual(self.timer.session_type, SessionType.WORK)
        self.assertEqual(self.timer.formatted_digits, "2500")
        self.assertEqual(self.timer.formatted_display, "25:00")

    def test_toggle_flow(self):
        # Idle -> Running
        self.timer.toggle()
        self.assertEqual(self.timer.state, TimerState.RUNNING)

        # Running -> Paused
        self.timer.toggle()
        self.assertEqual(self.timer.state, TimerState.PAUSED)

        # Paused -> Running
        self.timer.toggle()
        self.assertEqual(self.timer.state, TimerState.RUNNING)

    def test_countdown(self):
        self.timer.start()
        initial = self.timer.remaining_seconds
        res = self.timer.tick()
        self.assertTrue(res)
        self.assertEqual(self.timer.remaining_seconds, initial - 1)

    def test_completion_and_cycle(self):
        self.timer.start()
        self.timer.remaining_seconds = 1
        self.timer.tick()
        self.assertEqual(self.timer.state, TimerState.COMPLETED)

        # Advance to break
        self.timer.advance_to_next_session()
        self.assertEqual(self.timer.session_type, SessionType.SHORT_BREAK)
        self.assertEqual(self.timer.state, TimerState.IDLE)
        self.assertEqual(self.timer.formatted_digits, "0500")


class TestConfigAndStats(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch("sstp.config.CONFIG_DIR", Path(self.test_dir))
        self.patcher.start()
        self.patcher2 = patch("sstp.config.CONFIG_FILE", Path(self.test_dir) / "config.json")
        self.patcher2.start()
        self.cm = ConfigManager()

    def tearDown(self):
        self.patcher2.stop()
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_record_session_and_reset(self):
        self.cm.record_completed_session("work", 25)
        self.assertEqual(self.cm.stats["total_pomodoros_completed"], 1)
        self.assertEqual(self.cm.stats["total_focus_minutes"], 25)
        self.assertEqual(self.cm.stats["today_completed"], 1)
        self.assertEqual(self.cm.stats["daily_streak"], 1)

        self.cm.reset_statistics()
        self.assertEqual(self.cm.stats["total_pomodoros_completed"], 0)
        self.assertEqual(self.cm.stats["total_focus_minutes"], 0)
        self.assertEqual(self.cm.stats["today_completed"], 0)
        self.assertEqual(len(self.cm.stats["history"]), 0)


class TestLEDRenderer(unittest.TestCase):
    def test_digit_segments_and_centers(self):
        self.assertEqual(len(DIGIT_CENTERS), 4)
        for cx in DIGIT_CENTERS:
            segs = get_digit_segments(cx, DIGIT_CY)
            self.assertEqual(set(segs.keys()), {"a", "b", "c", "d", "e", "f", "g"})
            for k, pts in segs.items():
                self.assertGreaterEqual(len(pts), 4)

    def test_digit_map(self):
        for digit in "0123456789":
            self.assertIn(digit, DIGIT_MAP)
            self.assertGreater(len(DIGIT_MAP[digit]), 0)


class TestBreakTogglesAndOpacity( unittest.TestCase ):
    def setUp( self ):
        config.settings[ "work_minutes" ] = 25;
        config.settings[ "short_break_minutes" ] = 5;
        config.settings[ "long_break_minutes" ] = 15;
        config.settings[ "long_break_interval" ] = 4;
        config.settings[ "short_break_enabled" ] = True;
        config.settings[ "long_break_enabled" ] = True;
        self.timer = PomodoroTimer();

    def tearDown( self ):
        config.settings[ "short_break_enabled" ] = True;
        config.settings[ "long_break_enabled" ] = True;
        config.save();

    def test_short_break_disabled( self ):
        config.settings[ "short_break_enabled" ] = False;
        config.settings[ "long_break_enabled" ] = True;
        # Cycle 1: normally Short Break, but short break is disabled, so should advance to next Work session
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.WORK );

        # Cycles 2 and 3: Work
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.WORK );
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.WORK );

        # Cycle 4: 4th cycle with interval=4 and long_break_enabled=True -> LONG_BREAK
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.LONG_BREAK );

    def test_long_break_disabled( self ):
        config.settings[ "short_break_enabled" ] = True;
        config.settings[ "long_break_enabled" ] = False;
        # Cycle 4: interval reached, but long break is disabled, short break enabled -> SHORT_BREAK fallback
        self.timer.pomodoro_count = 3;
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.SHORT_BREAK );

    def test_both_breaks_disabled( self ):
        config.settings[ "short_break_enabled" ] = False;
        config.settings[ "long_break_enabled" ] = False;
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.WORK );
        self.timer.pomodoro_count = 3;
        self.timer.advance_to_next_session();
        self.assertEqual( self.timer.session_type, SessionType.WORK );

    def test_refresh_durations_with_disabled_break( self ):
        self.timer.session_type = SessionType.SHORT_BREAK;
        config.settings[ "short_break_enabled" ] = False;
        self.timer.refresh_durations();
        self.assertEqual( self.timer.session_type, SessionType.WORK );

    def test_settings_dialog_properties( self ):
        import gi;
        gi.require_version( "Gtk", "3.0" );
        from gi.repository import Gtk;
        from sstp.settings_dialog import SettingsDialog;
        parent = Gtk.Window();
        dialog = SettingsDialog( parent );
        self.assertAlmostEqual( Gtk.Widget.get_opacity( dialog ), 0.75, places=2 );
        self.assertTrue( hasattr( dialog, "chk_short" ) );
        self.assertTrue( hasattr( dialog, "chk_long" ) );
        self.assertEqual( dialog.chk_short.get_active(), config.settings[ "short_break_enabled" ] );
        self.assertEqual( dialog.chk_long.get_active(), config.settings[ "long_break_enabled" ] );
        dialog.destroy();
        parent.destroy();


if __name__ == "__main__":
    unittest.main()
