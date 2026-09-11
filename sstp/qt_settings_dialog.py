import os
import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QLabel,
        QSpinBox,
        QCheckBox,
        QSlider,
        QPushButton,
        QFileDialog,
        QMessageBox,
        QTabWidget,
        QWidget,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QPalette
except ImportError:
    from PySide6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QLabel,
        QSpinBox,
        QCheckBox,
        QSlider,
        QPushButton,
        QFileDialog,
        QMessageBox,
        QTabWidget,
        QWidget,
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette

from sstp.config import config, DEFAULT_SOUND_PATH
from sstp.audio import audio


class SettingsDialogQt(QDialog):
    """Cross-platform Settings and Statistics dialog for macOS, Windows, and Linux."""

    def __init__(self, parent=None, on_settings_changed=None):
        super().__init__(parent)
        self.setWindowTitle("SSTP — Machine Configuration & Logs")
        self.setModal(True)
        self.resize(520, 500)
        self.on_settings_changed = on_settings_changed

        self.setStyleSheet("""
            QDialog {
                background-color: rgba(43, 43, 46, 240);
                color: #e6e6e6;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #444448;
                background-color: #2b2b2e;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #1f1f22;
                color: #b0b0b0;
                padding: 8px 18px;
                border: 1px solid #333336;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2b2b2e;
                color: #ffffff;
                border-bottom: 1px solid #2b2b2e;
                font-weight: bold;
            }
            QLabel {
                color: #e6e6e6;
            }
            QSpinBox {
                background-color: #1e1e21;
                color: #ffffff;
                border: 1px solid #55555c;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QCheckBox {
                color: #e6e6e6;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #666;
                border-radius: 3px;
                background: #1e1e21;
            }
            QCheckBox::indicator:checked {
                background: #d33c2a;
                border-color: #ff5544;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e1e21;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #d33c2a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3e3e44;
                color: #ffffff;
                border: 1px solid #55555c;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #4e4e56;
            }
            QPushButton:pressed {
                background-color: #2e2e34;
            }
            QPushButton.destructive {
                background-color: #8b2518;
                border-color: #aa3322;
            }
            QPushButton.destructive:hover {
                background-color: #a82e1e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Timer Rules
        tab_timer = self._build_timer_tab()
        self.tabs.addTab(tab_timer, "Timer Rules")

        # Tab 2: Sound & FX
        tab_audio = self._build_audio_tab()
        self.tabs.addTab(tab_audio, "Sound & FX")

        # Tab 3: Statistics
        tab_stats = self._build_stats_tab()
        self.tabs.addTab(tab_stats, "Statistics")

        # Bottom buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _build_timer_tab(self) -> QWidget:
        w = QWidget()
        layout = QGridLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setVerticalSpacing(14)
        layout.setHorizontalSpacing(16)

        # Work Minutes
        lbl_work = QLabel("Working Time (minutes):")
        self.spin_work = QSpinBox()
        self.spin_work.setRange(1, 99)
        self.spin_work.setValue(config.settings.get("work_minutes", 25))
        self.spin_work.valueChanged.connect(self._on_durations_changed)
        layout.addWidget(lbl_work, 0, 0)
        layout.addWidget(self.spin_work, 0, 1)

        # Short Break
        self.chk_short = QCheckBox("Short Break (minutes):")
        self.chk_short.setChecked(config.settings.get("short_break_enabled", True))
        self.chk_short.toggled.connect(self._on_break_toggled)
        self.spin_short = QSpinBox()
        self.spin_short.setRange(1, 60)
        self.spin_short.setValue(config.settings.get("short_break_minutes", 5))
        self.spin_short.setEnabled(self.chk_short.isChecked())
        self.spin_short.valueChanged.connect(self._on_durations_changed)
        layout.addWidget(self.chk_short, 1, 0)
        layout.addWidget(self.spin_short, 1, 1)

        # Long Break
        self.chk_long = QCheckBox("Long Break (minutes):")
        self.chk_long.setChecked(config.settings.get("long_break_enabled", True))
        self.chk_long.toggled.connect(self._on_break_toggled)
        self.spin_long = QSpinBox()
        self.spin_long.setRange(1, 60)
        self.spin_long.setValue(config.settings.get("long_break_minutes", 15))
        self.spin_long.setEnabled(self.chk_long.isChecked())
        self.spin_long.valueChanged.connect(self._on_durations_changed)
        layout.addWidget(self.chk_long, 2, 0)
        layout.addWidget(self.spin_long, 2, 1)

        # Long Break Interval
        lbl_interval = QLabel("Long Break Interval (cycles):")
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 12)
        self.spin_interval.setValue(config.settings.get("long_break_interval", 4))
        self.spin_interval.setEnabled(self.chk_long.isChecked())
        self.spin_interval.valueChanged.connect(self._on_durations_changed)
        layout.addWidget(lbl_interval, 3, 0)
        layout.addWidget(self.spin_interval, 3, 1)

        desc = QLabel("Durations take effect on your next session cycle.")
        desc.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(desc, 4, 0, 1, 2)
        layout.setRowStretch(5, 1)
        return w

    def _build_audio_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Master Sound
        self.chk_master_sound = QCheckBox("Master Audio Sound")
        self.chk_master_sound.setChecked(config.settings.get("sound_enabled", True))
        self.chk_master_sound.toggled.connect(self._on_sound_toggled)
        layout.addWidget(self.chk_master_sound)

        # Tick Sound
        self.chk_tick_sound = QCheckBox("Mechanical / Digital Clock Ticking")
        self.chk_tick_sound.setChecked(config.settings.get("tick_sound_enabled", True))
        self.chk_tick_sound.toggled.connect(self._on_tick_toggled)
        layout.addWidget(self.chk_tick_sound)

        # Sound file selector
        lbl_file = QLabel("Ticking Sound Asset:")
        layout.addWidget(lbl_file)

        row_file = QHBoxLayout()
        self.lbl_sound_path = QLabel(os.path.basename(config.get_sound_file()))
        self.lbl_sound_path.setStyleSheet("color: #aaaaaa; font-family: monospace;")
        btn_choose = QPushButton("Choose File...")
        btn_choose.clicked.connect(self._on_choose_sound_file)
        btn_test = QPushButton("Preview")
        btn_test.clicked.connect(self._on_test_sound)
        btn_default = QPushButton("Default")
        btn_default.clicked.connect(self._on_reset_sound_file)

        row_file.addWidget(self.lbl_sound_path, 1)
        row_file.addWidget(btn_choose)
        row_file.addWidget(btn_test)
        row_file.addWidget(btn_default)
        layout.addLayout(row_file)

        # Volume Slider
        vol = config.settings.get("volume", 0.8)
        self.lbl_volume = QLabel(f"Audio Volume: {int(vol * 100)}%")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(int(vol * 100))
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.lbl_volume)
        layout.addWidget(self.slider_volume)

        # Vacuum Tube Glow
        self.chk_tube_glow = QCheckBox("Vacuum Tube Glow Animation")
        self.chk_tube_glow.setChecked(config.settings.get("tube_glow_enabled", True))
        self.chk_tube_glow.toggled.connect(self._on_fx_toggled)
        layout.addWidget(self.chk_tube_glow)

        # Machine Scale Slider
        scale = float(config.settings.get("scale", 0.5))
        self.lbl_scale = QLabel(f"Machine Size: {int(scale * 100)}%")
        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(30, 150)
        self.slider_scale.setValue(int(scale * 100))
        self.slider_scale.valueChanged.connect(self._on_scale_changed)
        layout.addWidget(self.lbl_scale)
        layout.addWidget(self.slider_scale)

        layout.addStretch()
        return w

    def _build_stats_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(20)

        stats = config.stats
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
            lbl_k = QLabel(k)
            lbl_v = QLabel(f"<b>{v}</b>")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(lbl_k, row, 0)
            grid.addWidget(lbl_v, row, 1)
            self.stat_labels[k] = lbl_v

        layout.addLayout(grid)
        layout.addStretch()

        btn_reset = QPushButton("Reset Statistics")
        btn_reset.setProperty("class", "destructive")
        btn_reset.setStyleSheet("background-color: #8b2518; color: white;")
        btn_reset.clicked.connect(self._on_reset_statistics)
        layout.addWidget(btn_reset)

        return w

    def _on_break_toggled(self):
        config.settings["short_break_enabled"] = self.chk_short.isChecked()
        config.settings["long_break_enabled"] = self.chk_long.isChecked()
        self.spin_short.setEnabled(self.chk_short.isChecked())
        self.spin_long.setEnabled(self.chk_long.isChecked())
        self.spin_interval.setEnabled(self.chk_long.isChecked())
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_durations_changed(self):
        config.settings["work_minutes"] = self.spin_work.value()
        config.settings["short_break_minutes"] = self.spin_short.value()
        config.settings["long_break_minutes"] = self.spin_long.value()
        config.settings["long_break_interval"] = self.spin_interval.value()
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_sound_toggled(self, checked):
        config.settings["sound_enabled"] = checked
        config.save()

    def _on_tick_toggled(self, checked):
        config.settings["tick_sound_enabled"] = checked
        config.save()

    def _on_fx_toggled(self, checked):
        config.settings["tube_glow_enabled"] = checked
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_choose_sound_file(self):
        fn, _ = QFileDialog.getOpenFileName(
            self,
            "Select Ticking Sound",
            os.path.dirname(config.get_sound_file()),
            "Audio Files (*.wav *.ogg *.mp3)",
        )
        if fn and os.path.exists(fn):
            config.settings["sound_file"] = fn
            config.save()
            self.lbl_sound_path.setText(os.path.basename(fn))

    def _on_reset_sound_file(self):
        config.settings["sound_file"] = DEFAULT_SOUND_PATH
        config.save()
        self.lbl_sound_path.setText(os.path.basename(DEFAULT_SOUND_PATH))

    def _on_test_sound(self):
        snd = config.get_sound_file()
        vol = config.settings.get("volume", 0.8)
        audio.test_sound(snd, vol)

    def _on_volume_changed(self, val):
        vol = val / 100.0
        config.settings["volume"] = vol
        self.lbl_volume.setText(f"Audio Volume: {int(vol * 100)}%")
        config.save()

    def _on_scale_changed(self, val):
        scale = round(val / 100.0, 2)
        config.settings["scale"] = scale
        self.lbl_scale.setText(f"Machine Size: {int(scale * 100)}%")
        config.save()
        if self.on_settings_changed:
            self.on_settings_changed()

    def _on_reset_statistics(self):
        res = QMessageBox.question(
            self,
            "Reset All Statistics?",
            "This will permanently clear all completed Pomodoros, logged focus time, streaks, and history.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if res == QMessageBox.StandardButton.Ok:
            config.reset_statistics()
            stats = config.stats
            self.stat_labels["Pomodoros Completed:"].setText(f"<b>{stats['total_pomodoros_completed']}</b>")
            self.stat_labels["Completed Today:"].setText(f"<b>{stats['today_completed']}</b>")
            self.stat_labels["Focus Time Logged:"].setText(f"<b>{stats['total_focus_minutes']} minutes</b>")
            self.stat_labels["Current Streak:"].setText(f"<b>{stats['daily_streak']} days</b>")
            self.stat_labels["Short Breaks Taken:"].setText(f"<b>{stats['total_short_breaks_completed']}</b>")
            self.stat_labels["Long Breaks Taken:"].setText(f"<b>{stats['total_long_breaks_completed']}</b>")
