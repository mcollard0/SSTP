import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from sstp.config import config, DEFAULT_SOUND_PATH
from sstp.audio import audio


class SettingsDialog(Gtk.Dialog):
    """Settings and Statistics dialog configured according to ARCHITECTURE.md."""

    def __init__(self, parent_window, on_settings_changed=None):
        super().__init__(
            title="SSTP — Machine Configuration & Logs",
            transient_for=parent_window,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(520, 480)
        self.on_settings_changed = on_settings_changed

        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)

        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(16)
        box.set_margin_end(16)

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # Tab 1: Timer Settings
        timer_box = self._build_timer_tab()
        notebook.append_page(timer_box, Gtk.Label(label="Timer Rules"))

        # Tab 2: Audio & Effects
        audio_box = self._build_audio_tab()
        notebook.append_page(audio_box, Gtk.Label(label="Sound & FX"))

        # Tab 3: Statistics
        stats_box = self._build_stats_tab()
        notebook.append_page(stats_box, Gtk.Label(label="Statistics"))

        self.connect("response", self._on_close)
        self.show_all()

    def _build_timer_tab(self) -> Gtk.Widget:
        grid = Gtk.Grid()
        grid.set_row_spacing(14)
        grid.set_column_spacing(16)
        grid.set_margin_top(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)

        # 1. Working time in minutes
        lbl_work = Gtk.Label(label="Working Time (minutes):", xalign=0)
        self.spin_work = Gtk.SpinButton.new_with_range(1, 120, 1)
        self.spin_work.set_value(config.settings.get("work_minutes", 25))
        self.spin_work.connect("value-changed", self._on_value_changed)
        grid.attach(lbl_work, 0, 0, 1, 1)
        grid.attach(self.spin_work, 1, 0, 1, 1)

        # Short break time
        lbl_short = Gtk.Label(label="Short Break (minutes):", xalign=0)
        self.spin_short = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.spin_short.set_value(config.settings.get("short_break_minutes", 5))
        self.spin_short.connect("value-changed", self._on_value_changed)
        grid.attach(lbl_short, 0, 1, 1, 1)
        grid.attach(self.spin_short, 1, 1, 1, 1)

        # Long break time
        lbl_long = Gtk.Label(label="Long Break (minutes):", xalign=0)
        self.spin_long = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.spin_long.set_value(config.settings.get("long_break_minutes", 15))
        self.spin_long.connect("value-changed", self._on_value_changed)
        grid.attach(lbl_long, 0, 2, 1, 1)
        grid.attach(self.spin_long, 1, 2, 1, 1)

        # Long break interval
        lbl_interval = Gtk.Label(label="Long Break Interval (cycles):", xalign=0)
        self.spin_interval = Gtk.SpinButton.new_with_range(1, 12, 1)
        self.spin_interval.set_value(config.settings.get("long_break_interval", 4))
        self.spin_interval.connect("value-changed", self._on_value_changed)
        grid.attach(lbl_interval, 0, 3, 1, 1)
        grid.attach(self.spin_interval, 1, 3, 1, 1)

        desc = Gtk.Label(
            label="Adjust durations for your focus sessions. Changes will take effect on the next session.",
            wrap=True,
            xalign=0,
        )
        desc.get_style_context().add_class("dim-label")
        grid.attach(desc, 0, 4, 2, 1)

        return grid

    def _build_audio_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        # 5. Sound toggle
        row_sound = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_sound = Gtk.Label(label="Master Audio Sound:", xalign=0)
        self.switch_sound = Gtk.Switch()
        self.switch_sound.set_active(config.settings.get("sound_enabled", True))
        self.switch_sound.connect("notify::active", self._on_sound_toggled)
        row_sound.pack_start(lbl_sound, True, True, 0)
        row_sound.pack_end(self.switch_sound, False, False, 0)
        box.pack_start(row_sound, False, False, 0)

        # Clock ticking toggle
        row_tick = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_tick = Gtk.Label(label="Mechanical / Digital Clock Ticking:", xalign=0)
        self.switch_tick = Gtk.Switch()
        self.switch_tick.set_active(config.settings.get("tick_sound_enabled", True))
        self.switch_tick.connect("notify::active", self._on_tick_toggled)
        row_tick.pack_start(lbl_tick, True, True, 0)
        row_tick.pack_end(self.switch_tick, False, False, 0)
        box.pack_start(row_tick, False, False, 0)

        # 6. Sound file selector (ship with basic digital clock ticking sound)
        box_file = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lbl_file = Gtk.Label(label="Ticking Sound Asset:", xalign=0)
        box_file.pack_start(lbl_file, False, False, 0)

        row_chooser = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.file_chooser = Gtk.FileChooserButton.new(
            "Select Ticking Sound", Gtk.FileChooserAction.OPEN
        )
        filt = Gtk.FileFilter()
        filt.set_name("Audio Files (*.wav, *.ogg, *.mp3)")
        filt.add_pattern("*.wav")
        filt.add_pattern("*.ogg")
        filt.add_pattern("*.mp3")
        self.file_chooser.add_filter(filt)

        current_sound = config.settings.get("sound_file", DEFAULT_SOUND_PATH)
        if os.path.exists(current_sound):
            self.file_chooser.set_filename(current_sound)
        self.file_chooser.connect("file-set", self._on_sound_file_set)

        btn_default = Gtk.Button(label="Reset Default")
        btn_default.connect("clicked", self._on_reset_sound_file)

        btn_test = Gtk.Button(label="Preview")
        btn_test.connect("clicked", self._on_test_sound)

        row_chooser.pack_start(self.file_chooser, True, True, 0)
        row_chooser.pack_start(btn_test, False, False, 0)
        row_chooser.pack_start(btn_default, False, False, 0)
        box_file.pack_start(row_chooser, False, False, 0)
        box.pack_start(box_file, False, False, 0)

        # 7. Sound volume slider
        box_vol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.lbl_volume = Gtk.Label(
            label=f"Audio Volume: {int(config.settings.get('volume', 0.8) * 100)}%",
            xalign=0,
        )
        self.scale_volume = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05
        )
        self.scale_volume.set_value(config.settings.get("volume", 0.8))
        self.scale_volume.connect("value-changed", self._on_volume_changed)
        box_vol.pack_start(self.lbl_volume, False, False, 0)
        box_vol.pack_start(self.scale_volume, False, False, 0)
        box.pack_start(box_vol, False, False, 0)

        # Vacuum tube glow toggle
        row_fx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_fx = Gtk.Label(label="Vacuum Tube Glow Animation:", xalign=0)
        self.switch_fx = Gtk.Switch()
        self.switch_fx.set_active(config.settings.get("tube_glow_enabled", True))
        self.switch_fx.connect("notify::active", self._on_fx_toggled)
        row_fx.pack_start(lbl_fx, True, True, 0)
        row_fx.pack_end(self.switch_fx, False, False, 0)
        box.pack_start(row_fx, False, False, 0)

        # Machine Size / Scale slider
        box_size = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        current_scale = float(config.settings.get("scale", 0.5))
        self.lbl_size = Gtk.Label(
            label=f"Machine Size: {int(current_scale * 100)}%",
            xalign=0,
        )
        self.scale_size = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.3, 1.5, 0.05
        )
        self.scale_size.set_value(current_scale)
        self.scale_size.connect("value-changed", self._on_size_changed)
        box_size.pack_start(self.lbl_size, False, False, 0)
        box_size.pack_start(self.scale_size, False, False, 0)
        box.pack_start(box_size, False, False, 0)

        return box

    def _build_stats_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_bottom(16)

        stats = config.stats

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(20)

        items = [
            ("Pomodoros Completed:", f"{stats.get('total_pomodoros_completed', 0)}"),
            ("Completed Today:", f"{stats.get('today_completed', 0)}"),
            ("Focus Time Logged:", f"{stats.get('total_focus_minutes', 0)} minutes"),
            ("Current Streak:", f"{stats.get('daily_streak', 0)} days"),
            ("Short Breaks Taken:", f"{stats.get('total_short_breaks_completed', 0)}"),
            ("Long Breaks Taken:", f"{stats.get('total_long_breaks_completed', 0)}"),
        ]

        self.stat_labels = {}
        for row, (k, v) in enumerate(items):
            lbl_k = Gtk.Label(label=k, xalign=0)
            lbl_v = Gtk.Label(label=f"<b>{v}</b>", xalign=1, use_markup=True)
            grid.attach(lbl_k, 0, row, 1, 1)
            grid.attach(lbl_v, 1, row, 1, 1)
            self.stat_labels[k] = lbl_v

        box.pack_start(grid, False, False, 0)

        # 8. Reset statistics button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_reset = Gtk.Button(label="Reset Statistics")
        btn_reset.get_style_context().add_class("destructive-action")
        btn_reset.connect("clicked", self._on_reset_statistics)
        btn_box.pack_start(btn_reset, False, False, 0)
        box.pack_end(btn_box, False, False, 0)

        return box

    def _on_value_changed(self, spin):
        config.settings["work_minutes"] = int(self.spin_work.get_value())
        config.settings["short_break_minutes"] = int(self.spin_short.get_value())
        config.settings["long_break_minutes"] = int(self.spin_long.get_value())
        config.settings["long_break_interval"] = int(self.spin_interval.get_value())
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_sound_toggled(self, switch, gparam):
        config.settings["sound_enabled"] = switch.get_active()
        config.save()

    def _on_tick_toggled(self, switch, gparam):
        config.settings["tick_sound_enabled"] = switch.get_active()
        config.save()

    def _on_fx_toggled(self, switch, gparam):
        config.settings["tube_glow_enabled"] = switch.get_active()
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_sound_file_set(self, chooser):
        path = chooser.get_filename()
        if path and os.path.exists(path):
            config.settings["sound_file"] = path
            config.save()

    def _on_reset_sound_file(self, btn):
        config.settings["sound_file"] = DEFAULT_SOUND_PATH
        self.file_chooser.set_filename(DEFAULT_SOUND_PATH)
        config.save()

    def _on_test_sound(self, btn):
        path = self.file_chooser.get_filename() or config.settings.get("sound_file", DEFAULT_SOUND_PATH)
        vol = self.scale_volume.get_value()
        audio.test_sound(path, vol)

    def _on_volume_changed(self, scale):
        vol = scale.get_value()
        config.settings["volume"] = vol
        self.lbl_volume.set_text(f"Audio Volume: {int(vol * 100)}%")
        config.save()

    def _on_size_changed(self, scale):
        val = round(scale.get_value(), 2)
        config.settings["scale"] = val
        self.lbl_size.set_text(f"Machine Size: {int(val * 100)}%")
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_reset_statistics(self, btn):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Reset All Statistics?",
        )
        dialog.format_secondary_text(
            "This will permanently clear all completed Pomodoros, logged focus time, streaks, and history."
        )
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            config.reset_statistics()
            stats = config.stats
            self.stat_labels["Pomodoros Completed:"].set_markup(f"<b>{stats['total_pomodoros_completed']}</b>")
            self.stat_labels["Completed Today:"].set_markup(f"<b>{stats['today_completed']}</b>")
            self.stat_labels["Focus Time Logged:"].set_markup(f"<b>{stats['total_focus_minutes']} minutes</b>")
            self.stat_labels["Current Streak:"].set_markup(f"<b>{stats['daily_streak']} days</b>")
            self.stat_labels["Short Breaks Taken:"].set_markup(f"<b>{stats['total_short_breaks_completed']}</b>")
            self.stat_labels["Long Breaks Taken:"].set_markup(f"<b>{stats['total_long_breaks_completed']}</b>")

    def _on_close(self, dialog, response_id):
        self.destroy()
