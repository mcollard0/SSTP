import os
import sys
import time
import math
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import cairo

from sstp.config import config
from sstp.timer import PomodoroTimer, TimerState, SessionType
from sstp.audio import audio
from sstp.tray import SystemTrayManager
from sstp.settings_dialog import SettingsDialog
from sstp.led_renderer import render_led_overlay, render_tube_glow

MACHINE_IMG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "outputs", "machine.png")
)
ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
)


class PomodoroMachineApp(Gtk.Window):
    """Main desktop application window hosting the retro machine interface."""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Stuart Saves the Pomodoro")
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Set window icon
        if os.path.exists(ICON_PATH):
            self.set_icon_from_file(ICON_PATH)

        # Windowless configuration: no titlebar, no borders, no CSD decoration
        self.set_decorated( False );
        empty_header = Gtk.Fixed();
        empty_header.set_size_request( 0, 0 );
        self.set_titlebar( empty_header );
        self.set_type_hint( Gdk.WindowTypeHint.NORMAL );
        self.set_skip_taskbar_hint( False );

        # Configure RGBA visual for desktop transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.set_app_paintable(True)
            self.composited = True
        else:
            self.composited = False

        # CSS provider to guarantee zero background, border, or shadow from GTK themes
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window, .background, decoration, headerbar {
                background-color: transparent;
                background-image: none;
                border-width: 0;
                box-shadow: none;
                padding: 0;
                margin: 0;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Load machine image surface
        if not os.path.exists(MACHINE_IMG_PATH):
            raise FileNotFoundError(f"Machine asset not found at {MACHINE_IMG_PATH}")
        self.machine_surface = cairo.ImageSurface.create_from_png(MACHINE_IMG_PATH)
        self.img_width = self.machine_surface.get_width()
        self.img_height = self.machine_surface.get_height()

        self.scale = float(config.settings.get("scale", 0.5))
        init_w = int(self.img_width * self.scale)
        init_h = int(self.img_height * self.scale)
        self.set_default_size(init_w, init_h)

        # Initialize Timer
        self.timer = PomodoroTimer()
        self.timer.on_tick = self._on_timer_tick
        self.timer.on_state_changed = self._on_state_changed
        self.timer.on_session_completed = self._on_session_completed

        # Animation state
        self.pulse_phase = 0.0
        self.colon_visible = True
        self.hover_zone = None  # "dial", "buttons", "cartridge", None
        self.red_button_pressed = False
        self.white_buttons_pressed = False

        # Drawing Area
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_size_request(init_w, init_h)
        self.draw_area.connect("draw", self._on_draw)

        # Event handling
        self.draw_area.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.draw_area.connect("button-press-event", self._on_button_press)
        self.draw_area.connect("button-release-event", self._on_button_release)
        self.draw_area.connect("motion-notify-event", self._on_motion_notify)
        self.draw_area.connect("leave-notify-event", self._on_leave_notify)
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_delete_event)

        self.add(self.draw_area)

        # System Tray Integration
        self.tray = SystemTrayManager(self, self.timer, self.open_settings)
        self._update_tray_status()

        # Timers
        GLib.timeout_add(50, self._on_anim_timer)
        GLib.timeout_add_seconds(1, self._on_second_timer)

    def _update_tray_status(self):
        text = f"{self.timer.session_type.name}: {self.timer.formatted_display} ({self.timer.state.name})"
        self.tray.update_tooltip(text)

    def _on_timer_tick(self, remaining: int, total: int):
        self._update_tray_status()
        self.draw_area.queue_draw()

    def _on_state_changed(self, new_state: TimerState):
        self._update_tray_status()
        self.draw_area.queue_draw()

    def _on_session_completed(self, session_type: SessionType, duration_mins: int):
        audio.play_alarm()
        if session_type == SessionType.WORK:
            title = "Pomodoro Completed! 🍅"
            msg = f"Great job! You finished a {duration_mins} minute focus session. Time for a well-earned break!"
        else:
            title = "Break Finished! ⚡"
            msg = "Break time is over. Ready to begin your next focus session?"

        self.tray.send_notification(title, msg)
        self.timer.advance_to_next_session()
        self._update_tray_status()
        self.draw_area.queue_draw()

    def _on_second_timer(self) -> bool:
        if self.timer.state == TimerState.RUNNING:
            self.timer.tick()
            audio.play_tick()
        self.colon_visible = not self.colon_visible
        self.draw_area.queue_draw()
        return True

    def _on_anim_timer(self) -> bool:
        self.pulse_phase += 0.05
        if self.timer.state == TimerState.RUNNING:
            self.draw_area.queue_draw()
        return True

    def _is_in_red_circle(self, x: float, y: float) -> bool:
        # Center of circular yellow dial in machine.png is (158.0, 402.0) with radius 56px
        cx, cy = 158.0, 402.0
        dist = math.hypot(x - cx, y - cy)
        return dist <= 56.0

    def _is_in_white_buttons(self, x: float, y: float) -> bool:
        # 4 white rectangular buttons arranged in 2x2 grid
        # Enclosing bounding box: x: 110..244, y: 584..656
        return 110.0 <= x <= 244.0 and 584.0 <= y <= 656.0

    def _is_in_cartridge(self, x: float, y: float) -> bool:
        # Brass jack & cartridge slot: x: 310..470, y: 310..480
        return 310.0 <= x <= 470.0 and 310.0 <= y <= 480.0

    def _on_motion_notify(self, widget, event):
        x, y = event.x / self.scale, event.y / self.scale
        old_zone = self.hover_zone
        if self._is_in_red_circle(x, y):
            self.hover_zone = "dial"
            self.draw_area.set_tooltip_text(
                f"Main Power Switch: Click to {'Pause' if self.timer.state == TimerState.RUNNING else 'Start'} Pomodoro"
            )
        elif self._is_in_white_buttons(x, y):
            self.hover_zone = "buttons"
            self.draw_area.set_tooltip_text(
                "Control Buttons: Click to open Settings & Statistics"
            )
        elif self._is_in_cartridge(x, y):
            self.hover_zone = "cartridge"
            self.draw_area.set_tooltip_text(
                f"Cartridge Bay: Current Mode: [{self.timer.session_type.name}]. Click to switch Work/Break"
            )
        elif 315.0 <= x <= 445.0 and 575.0 <= y <= 625.0:
            self.hover_zone = "led"
            self.draw_area.set_tooltip_text(
                f"Chronometer Display: {self.timer.formatted_display} remaining"
            )
        else:
            self.hover_zone = None
            self.draw_area.set_tooltip_text("Stuart Saves the Pomodoro (Drag anywhere on casing to move)")

        if self.hover_zone != old_zone:
            self.draw_area.queue_draw()

    def _on_leave_notify(self, widget, event):
        self.hover_zone = None
        self.red_button_pressed = False
        self.white_buttons_pressed = False
        self.draw_area.queue_draw()

    def _on_button_press(self, widget, event):
        if event.button == 1:  # Left click
            x, y = event.x / self.scale, event.y / self.scale
            if self._is_in_red_circle(x, y):
                # 1. Red button: stops / starts / restarts timer
                self.red_button_pressed = True
                audio.play_click()
                self.timer.toggle()
                self.draw_area.queue_draw()
                return True
            elif self._is_in_white_buttons(x, y):
                # 2. White button: opens settings dialog
                self.white_buttons_pressed = True
                audio.play_click()
                self.draw_area.queue_draw()
                self.open_settings()
                return True
            elif self._is_in_cartridge( x, y ):
                # Mode switcher: Work <-> Break
                audio.play_click();
                short_enabled = config.settings.get( "short_break_enabled", True );
                long_enabled = config.settings.get( "long_break_enabled", True );
                if self.timer.session_type == SessionType.WORK:
                    if short_enabled:
                        self.timer.set_session_type( SessionType.SHORT_BREAK );
                    elif long_enabled:
                        self.timer.set_session_type( SessionType.LONG_BREAK );
                else:
                    self.timer.set_session_type( SessionType.WORK );
                self.draw_area.queue_draw();
                return True;
            else:
                # Drag window
                self.begin_move_drag(
                    event.button, int(event.x_root), int(event.y_root), event.time
                )
                return True
        elif event.button == 3:  # Right click
            # Context menu
            self.tray._on_popup_menu(None, event.button, event.time)
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1:
            self.red_button_pressed = False
            self.white_buttons_pressed = False
            self.draw_area.queue_draw()
            return True
        return False

    def _on_key_press(self, widget, event):
        keyval = event.keyval
        if keyval == Gdk.KEY_space:
            audio.play_click()
            self.timer.toggle()
            return True
        elif keyval in (Gdk.KEY_s, Gdk.KEY_S):
            self.open_settings()
            return True
        elif keyval in (Gdk.KEY_r, Gdk.KEY_R):
            audio.play_click()
            self.timer.reset()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        elif keyval in (Gdk.KEY_q, Gdk.KEY_Q):
            Gtk.main_quit()
            return True
        return False

    def open_settings(self):
        def _on_changed():
            new_scale = float(config.settings.get("scale", 0.5))
            if abs(new_scale - self.scale) > 0.001:
                self.scale = new_scale
                target_w = int(self.img_width * self.scale)
                target_h = int(self.img_height * self.scale)
                self.draw_area.set_size_request(target_w, target_h)
                self.resize(target_w, target_h)
            self.timer.refresh_durations()
            self.draw_area.queue_draw()

        dlg = SettingsDialog(self, on_settings_changed=_on_changed)
        dlg.run()

    def _on_draw(self, widget, cr: cairo.Context):
        # Clear background (transparent if composited)
        if self.composited:
            cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
        else:
            cr.set_source_rgb(0.12, 0.12, 0.14)
            cr.paint()

        # Apply global machine scale factor
        cr.scale(self.scale, self.scale)

        # 1. Paint machine base image
        cr.set_source_surface(self.machine_surface, 0, 0)
        cr.paint()

        # 2. Vacuum tube pulsing glow (when timer running)
        if (
            self.timer.state == TimerState.RUNNING
            and config.settings.get("tube_glow_enabled", True)
        ):
            render_tube_glow(cr, self.pulse_phase)

        # 3. Red rotary switch interaction overlay
        # Center: (158.0, 402.0)
        if self.timer.state == TimerState.RUNNING:
            # Active neon indicator rim around dial
            cr.save()
            cr.arc(158.0, 402.0, 50.0, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.2, 0.1, 0.35 + 0.15 * math.sin(self.pulse_phase * 3.0))
            cr.set_line_width(3.0)
            cr.stroke()
            cr.restore()

        if self.hover_zone == "dial":
            cr.save()
            cr.arc(158.0, 402.0, 54.0, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.9, 0.3, 0.2)
            cr.fill()
            cr.restore()

        # 4. White buttons hover / press overlay
        if self.hover_zone == "buttons" or self.white_buttons_pressed:
            cr.save()
            # Highlight the 4 buttons
            btn_coords = [
                (114, 587, 54, 23),
                (184, 587, 56, 23),
                (114, 629, 54, 24),
                (184, 629, 56, 24),
            ]
            for bx, by, bw, bh in btn_coords:
                cr.rectangle(bx, by, bw, bh)
                if self.white_buttons_pressed:
                    cr.set_source_rgba(0.2, 0.6, 1.0, 0.35)
                else:
                    cr.set_source_rgba(1.0, 1.0, 0.8, 0.25)
                cr.fill()
            cr.restore()

        # 5. LED Display Overlay
        # Red LED countdown time overlay over unlit segments
        show_col = (
            self.colon_visible
            if self.timer.state == TimerState.RUNNING
            else True
        )
        render_led_overlay(
            cr,
            self.timer.formatted_digits,
            show_colon=show_col,
            intensity=1.0,
            active=True,
        )

        return False

    def _on_delete_event(self, widget, event):
        # Minimize to tray instead of quitting
        self.hide()
        return True


def main():
    GLib.set_prgname( "sstp" );
    GLib.set_application_name( "Stuart Saves the Pomodoro" );
    if os.path.exists( ICON_PATH ):
        Gtk.Window.set_default_icon_from_file( ICON_PATH );
    app = PomodoroMachineApp();
    app.show_all();
    Gtk.main();


if __name__ == "__main__":
    main()
