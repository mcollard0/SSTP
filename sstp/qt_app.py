import os
import sys
import math
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QMenu,
        QSystemTrayIcon,
        QToolTip,
    )
    from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
    from PyQt6.QtGui import (
        QPainter,
        QPixmap,
        QColor,
        QIcon,
        QAction,
        QCursor,
        QPen,
        QBrush,
    )
except ImportError:
    from PySide6.QtWidgets import (
        QApplication,
        QWidget,
        QMenu,
        QSystemTrayIcon,
        QToolTip,
    )
    from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
    from PySide6.QtGui import (
        QPainter,
        QPixmap,
        QColor,
        QIcon,
        QAction,
        QCursor,
        QPen,
        QBrush,
    )

from sstp.config import config
from sstp.timer import PomodoroTimer, TimerState, SessionType
from sstp.audio import audio
from sstp.led_renderer import render_led_overlay_qt, render_tube_glow_qt
from sstp.qt_settings_dialog import SettingsDialogQt

from sstp.const import MACHINE_IMG_PATH, ICON_PATH, VERSION


class PomodoroMachineQtApp(QWidget):
    """Universal cross-platform desktop Pomodoro timer (macOS, Windows, Linux)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stuart Saves the Pomodoro")

        # Windowless frameless transparent configuration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Set Window Icon
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        # Load machine background asset
        if not os.path.exists(MACHINE_IMG_PATH):
            raise FileNotFoundError(f"Machine asset not found at {MACHINE_IMG_PATH}")
        self.machine_pixmap = QPixmap(MACHINE_IMG_PATH)
        self.img_width = self.machine_pixmap.width()
        self.img_height = self.machine_pixmap.height()

        self.scale = float(config.settings.get("scale", 0.5))
        self._apply_scale_size()

        # Initialize Timer
        self.timer = PomodoroTimer()
        self.timer.on_tick = self._on_timer_tick
        self.timer.on_state_changed = self._on_state_changed
        self.timer.on_session_completed = self._on_session_completed

        # Animation and interaction state
        self.pulse_phase = 0.0
        self.colon_visible = True
        self.hover_zone = None
        self.red_button_pressed = False
        self.white_buttons_pressed = False
        self.drag_position = None
        self.settings_dialog = None

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Setup System Tray
        self._setup_system_tray()

        # Timers
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_timer)
        self.anim_timer.start(50)

        self.second_timer = QTimer(self)
        self.second_timer.timeout.connect(self._on_second_timer)
        self.second_timer.start(1000)

        self._update_tray_status()

    def _apply_scale_size(self):
        w = int(self.img_width * self.scale)
        h = int(self.img_height * self.scale)
        self.setFixedSize(w, h)

    def _setup_system_tray(self):
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(ICON_PATH):
            self.tray.setIcon(QIcon(ICON_PATH))

        self.tray_menu = QMenu()

        self.tray_status_action = QAction("SSTP Pomodoro", self)
        self.tray_status_action.setEnabled(False)
        self.tray_menu.addAction(self.tray_status_action)
        self.tray_menu.addSeparator()

        self.action_toggle = QAction("Start Timer", self)
        self.action_toggle.triggered.connect(self.timer.toggle)
        self.tray_menu.addAction(self.action_toggle)

        self.action_skip = QAction("Skip to Next Session", self)
        self.action_skip.triggered.connect(self.timer.advance_to_next_session)
        self.tray_menu.addAction(self.action_skip)

        self.action_reset = QAction("Reset Timer", self)
        self.action_reset.triggered.connect(self.timer.reset)
        self.tray_menu.addAction(self.action_reset)
        self.tray_menu.addSeparator()

        self.action_settings = QAction("Settings & Stats...", self)
        self.action_settings.triggered.connect(self.open_settings)
        self.tray_menu.addAction(self.action_settings)

        self.action_visibility = QAction("Hide Window", self)
        self.action_visibility.triggered.connect(self._toggle_window_visibility)
        self.tray_menu.addAction(self.action_visibility)
        self.tray_menu.addSeparator()

        self.action_quit = QAction("Quit SSTP", self)
        self.action_quit.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(self.action_quit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _update_tray_status(self):
        status = f"{self.timer.session_type.name}: {self.timer.formatted_display} ({self.timer.state.name})"
        self.tray.setToolTip(f"Stuart Pomodoro: {status}")
        self.tray_status_action.setText(f"[{self.timer.session_type.name}] {self.timer.formatted_display}")
        if self.timer.state == TimerState.RUNNING:
            self.action_toggle.setText("Pause Timer")
        else:
            self.action_toggle.setText("Start Timer")

    def _toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
            self.action_visibility.setText("Show Window")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.action_visibility.setText("Hide Window")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window_visibility()

    def _on_timer_tick(self, remaining: int, total: int):
        self._update_tray_status()
        self.update()

    def _on_state_changed(self, new_state: TimerState):
        self._update_tray_status()
        self.update()

    def _on_session_completed(self, session_type: SessionType, duration_mins: int):
        audio.play_alarm()
        if session_type == SessionType.WORK:
            title = "Pomodoro Completed! 🍅"
            msg = f"Great job! You finished a {duration_mins} minute focus session. Time for a well-earned break!"
        else:
            title = "Break Finished! ⚡"
            msg = "Break time is over. Ready to begin your next focus session?"

        self.tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 6000)
        self.timer.advance_to_next_session()
        self._update_tray_status()
        self.update()

    def _on_second_timer(self):
        if self.timer.state == TimerState.RUNNING:
            self.timer.tick()
            audio.play_tick()
        self.colon_visible = not self.colon_visible
        self.update()

    def _on_anim_timer(self):
        self.pulse_phase += 0.05
        if self.timer.state == TimerState.RUNNING:
            self.update()

    def _is_in_red_circle(self, x: float, y: float) -> bool:
        cx, cy = 158.0, 402.0
        return math.hypot(x - cx, y - cy) <= 56.0

    def _is_in_white_buttons(self, x: float, y: float) -> bool:
        return 110.0 <= x <= 244.0 and 584.0 <= y <= 656.0

    def _is_in_cartridge(self, x: float, y: float) -> bool:
        return 310.0 <= x <= 470.0 and 310.0 <= y <= 480.0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position() if hasattr(event, "position") else event.localPos()
            x = pos.x() / self.scale
            y = pos.y() / self.scale

            if self._is_in_red_circle(x, y):
                self.red_button_pressed = True
                audio.play_click()
                self.timer.toggle()
                self.update()
            elif self._is_in_white_buttons(x, y):
                self.white_buttons_pressed = True
                audio.play_click()
                self.update()
                self.open_settings()
            elif self._is_in_cartridge(x, y):
                audio.play_click()
                short_enabled = config.settings.get("short_break_enabled", True)
                long_enabled = config.settings.get("long_break_enabled", True)
                if self.timer.session_type == SessionType.WORK:
                    if short_enabled:
                        self.timer.set_session_type(SessionType.SHORT_BREAK)
                    elif long_enabled:
                        self.timer.set_session_type(SessionType.LONG_BREAK)
                else:
                    self.timer.set_session_type(SessionType.WORK)
                self.update()
            else:
                # Initiate window dragging
                win_handle = self.windowHandle()
                if win_handle and hasattr(win_handle, "startSystemMove") and win_handle.startSystemMove():
                    pass
                else:
                    global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
                    self.drag_position = global_pos - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.tray_menu.exec(global_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.red_button_pressed = False
            self.white_buttons_pressed = False
            self.drag_position = None
            self.update()

    def mouseMoveEvent(self, event):
        # Fallback drag
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_position is not None:
            global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self.move(global_pos - self.drag_position)
            return

        pos = event.position() if hasattr(event, "position") else event.localPos()
        x = pos.x() / self.scale
        y = pos.y() / self.scale
        old_zone = self.hover_zone

        if self._is_in_red_circle(x, y):
            self.hover_zone = "dial"
            action = "Pause" if self.timer.state == TimerState.RUNNING else "Start"
            self.setToolTip(f"Main Power Switch: Click to {action} Pomodoro")
        elif self._is_in_white_buttons(x, y):
            self.hover_zone = "buttons"
            self.setToolTip("Control Buttons: Click to open Settings & Statistics")
        elif self._is_in_cartridge(x, y):
            self.hover_zone = "cartridge"
            self.setToolTip(f"Cartridge Bay: [{self.timer.session_type.name}]. Click to switch Work/Break")
        elif 315.0 <= x <= 445.0 and 575.0 <= y <= 625.0:
            self.hover_zone = "led"
            self.setToolTip(f"Chronometer Display: {self.timer.formatted_display} remaining")
        else:
            self.hover_zone = None
            self.setToolTip("Stuart Saves the Pomodoro (Drag anywhere on casing to move)")

        if self.hover_zone != old_zone:
            self.update()

    def leaveEvent(self, event):
        self.hover_zone = None
        self.red_button_pressed = False
        self.white_buttons_pressed = False
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            audio.play_click()
            self.timer.toggle()
        elif key == Qt.Key.Key_S:
            self.open_settings()
        elif key == Qt.Key.Key_R:
            audio.play_click()
            self.timer.reset()
        elif key == Qt.Key.Key_Escape:
            self.hide()
            self.action_visibility.setText("Show Window")
        elif key == Qt.Key.Key_Q:
            QApplication.instance().quit()

    def open_settings(self):
        if self.settings_dialog and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return

        def _on_changed():
            new_scale = float(config.settings.get("scale", 0.5))
            if abs(new_scale - self.scale) > 0.001:
                self.scale = new_scale
                self._apply_scale_size()
            self.timer.refresh_durations()
            self.update()

        self.settings_dialog = SettingsDialogQt(self, on_settings_changed=_on_changed)
        self.settings_dialog.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Scale coordinate space
        painter.scale(self.scale, self.scale)

        # 1. Base machine PNG
        painter.drawPixmap(0, 0, self.machine_pixmap)

        # 2. Vacuum Tube breathing glow
        if self.timer.state == TimerState.RUNNING and config.settings.get("tube_glow_enabled", True):
            render_tube_glow_qt(painter, self.pulse_phase)

        # 3. Red rotary switch dial active indicator & hover
        if self.timer.state == TimerState.RUNNING:
            glow = 0.35 + 0.15 * math.sin(self.pulse_phase * 3.0)
            pen = QPen(QColor(255, 51, 25, int(255 * glow)), 3.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(158.0, 402.0), 50.0, 50.0)

        if self.hover_zone == "dial":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 230, 77, 50))
            painter.drawEllipse(QPointF(158.0, 402.0), 54.0, 54.0)

        # 4. White buttons hover / press highlight
        if self.hover_zone == "buttons" or self.white_buttons_pressed:
            btn_coords = [
                (114, 587, 54, 23),
                (184, 587, 56, 23),
                (114, 629, 54, 24),
                (184, 629, 56, 24),
            ]
            fill_color = QColor(50, 150, 255, 90) if self.white_buttons_pressed else QColor(255, 255, 204, 64)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            for bx, by, bw, bh in btn_coords:
                painter.drawRect(bx, by, bw, bh)

        # 5. Glowing Red 7-Segment LED Countdown Display
        show_col = self.colon_visible if self.timer.state == TimerState.RUNNING else True
        render_led_overlay_qt(
            painter,
            self.timer.formatted_digits,
            show_colon=show_col,
            intensity=1.0,
            active=True,
        )

    def closeEvent(self, event):
        if self.tray.isVisible():
            self.hide()
            self.action_visibility.setText("Show Window")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stuart Saves the Pomodoro")
    app.setOrganizationName("SSTP")
    app.setQuitOnLastWindowClosed(False)

    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = PomodoroMachineQtApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
