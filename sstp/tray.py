import os
import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify

    NOTIFY_AVAILABLE = True
except Exception:
    NOTIFY_AVAILABLE = False

from gi.repository import Gtk, GdkPixbuf
from sstp.timer import TimerState, SessionType

ICON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
)


class SystemTrayManager:
    """GTK+ System Tray integration with Gtk.StatusIcon and desktop notifications."""

    def __init__(self, main_window, timer, on_open_settings):
        self.main_window = main_window
        self.timer = timer
        self.on_open_settings = on_open_settings
        self.status_icon = None

        if NOTIFY_AVAILABLE:
            try:
                Notify.init("Stuart Saves the Pomodoro")
            except Exception as e:
                print(f"[Tray] Notify init error: {e}")

        self._setup_status_icon()

    def _setup_status_icon(self):
        try:
            self.status_icon = Gtk.StatusIcon()
            if os.path.exists(ICON_PATH):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(ICON_PATH, 32, 32, True)
                self.status_icon.set_from_pixbuf(pixbuf)
            else:
                self.status_icon.set_from_icon_name("alarm")

            self.status_icon.set_title("Stuart Saves the Pomodoro")
            self.status_icon.set_tooltip_text("Stuart Saves the Pomodoro")
            self.status_icon.set_visible(True)

            self.status_icon.connect("activate", self._on_activate)
            self.status_icon.connect("popup-menu", self._on_popup_menu)
        except Exception as e:
            print(f"[Tray] Failed to initialize Gtk.StatusIcon: {e}")

    def update_tooltip(self, text: str):
        if self.status_icon:
            self.status_icon.set_tooltip_text(f"Stuart Pomodoro: {text}")

    def send_notification(self, title: str, message: str):
        if NOTIFY_AVAILABLE:
            try:
                notif = Notify.Notification.new(title, message, ICON_PATH if os.path.exists(ICON_PATH) else "alarm")
                notif.show()
                return
            except Exception as e:
                print(f"[Tray] Notification error: {e}")

        # Fallback to notify-send
        try:
            import subprocess
            subprocess.Popen(["notify-send", "-i", ICON_PATH, title, message])
        except Exception:
            pass

    def _on_activate(self, status_icon):
        """Toggle main window visibility."""
        if self.main_window.is_visible():
            self.main_window.hide()
        else:
            self.main_window.show_all()
            self.main_window.present()

    def _on_popup_menu(self, status_icon, button, activate_time):
        menu = Gtk.Menu()

        # Status item
        status_label = f"[{self.timer.session_type.name}] {self.timer.formatted_display}"
        item_status = Gtk.MenuItem(label=status_label)
        item_status.set_sensitive(False)
        menu.append(item_status)

        menu.append(Gtk.SeparatorMenuItem())

        # Start / Pause toggle
        if self.timer.state == TimerState.RUNNING:
            item_toggle = Gtk.MenuItem(label="Pause Timer")
        else:
            item_toggle = Gtk.MenuItem(label="Start Timer")
        item_toggle.connect("activate", lambda _: self.timer.toggle())
        menu.append(item_toggle)

        # Skip
        item_skip = Gtk.MenuItem(label="Skip to Next Session")
        item_skip.connect("activate", lambda _: self.timer.advance_to_next_session())
        menu.append(item_skip)

        # Reset
        item_reset = Gtk.MenuItem(label="Reset Timer")
        item_reset.connect("activate", lambda _: self.timer.reset())
        menu.append(item_reset)

        menu.append(Gtk.SeparatorMenuItem())

        # Settings
        item_settings = Gtk.MenuItem(label="Settings & Stats...")
        item_settings.connect("activate", lambda _: self.on_open_settings())
        menu.append(item_settings)

        # Show / Hide
        vis_label = "Hide Window" if self.main_window.is_visible() else "Show Window"
        item_vis = Gtk.MenuItem(label=vis_label)
        item_vis.connect("activate", self._on_activate)
        menu.append(item_vis)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        item_quit = Gtk.MenuItem(label="Quit SSTP")
        item_quit.connect("activate", lambda _: Gtk.main_quit())
        menu.append(item_quit)

        menu.show_all()
        if status_icon:
            menu.popup(None, None, Gtk.StatusIcon.position_menu, status_icon, button, activate_time)
        else:
            menu.popup(None, None, None, None, button, activate_time)
