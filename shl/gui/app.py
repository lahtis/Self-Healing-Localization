"""GTK4 Application for SHL 2.0.

Orchestrates: config → splash → preload → main window.
"""
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from shl.gui.app_config import AppConfig
from shl.gui.localizer import GuiLocalizer
from shl.gui.paths import Paths
from shl.gui.preload import preload
from shl.gui.splash import SplashWindow
from shl.gui.window import MainWindow

MIN_SPLASH_SECONDS = 0.6


class ShlGuiApp(Gtk.Application):
    """SHL 2.0 GTK4 application."""

    def __init__(self, argv=None):
        super().__init__(application_id="org.shl.gui")
        self.argv = argv or []
        self._parse_args()

        self.config = None
        self.localizer = None
        self.splash = None
        self.main_window = None
        self._preload_events = None
        self._start_time = 0.0

    def _parse_args(self):
        """Parse minimal CLI args: app_name, lang_code, source_path."""
        args = [a for a in self.argv[1:] if not a.startswith("-")]
        self.app_name = args[0] if len(args) > 0 else "shl-gui"
        self.lang_code = args[1] if len(args) > 1 else "en"
        self.source_path = Path(args[2]) if len(args) > 2 else Path.cwd()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Paths.ensure_all(self.app_name)
        self.config = AppConfig(self.app_name)
        if self.lang_code == "en":
            self.lang_code = self.config.language
        self.localizer = GuiLocalizer(self.app_name, self.lang_code)

    def do_activate(self):
        if self.main_window:
            self.main_window.present()
            return

        self.splash = SplashWindow(application=self)
        self.splash.present()

        self._start_time = time.monotonic()
        self._preload_events = preload(
            source_path=self.source_path,
            app_name=self.app_name,
            lang_code=self.lang_code,
            base_lang=self.config.base_lang,
        )

        # Give splash one frame to draw
        GLib.timeout_add(100, self._step_preload)

    def _step_preload(self):
        try:
            event = next(self._preload_events)
        except StopIteration:
            self._finish_startup()
            return False
        except Exception as exc:
            if self.splash:
                self.splash.set_status(f"Error: {exc}", 1.0)
            GLib.timeout_add(1500, self._finish_startup)
            return False

        fraction = event.phase_fraction
        if event.kind == "translate" and event.total > 0:
            fraction = event.key_fraction

        if self.splash:
            self.splash.set_status(event.message, fraction)

        GLib.timeout_add(16, self._step_preload)
        return False

    def _finish_startup(self):
        elapsed = time.monotonic() - self._start_time
        delay_ms = max(1, int((MIN_SPLASH_SECONDS - elapsed) * 1000))
        GLib.timeout_add(delay_ms, self._open_main)
        return False

    def _open_main(self):
        self.localizer = GuiLocalizer(self.app_name, self.lang_code)
        if not self.main_window:
            self.main_window = MainWindow(
                application=self,
                localizer=self.localizer,
                app_name=self.app_name,
                lang_code=self.lang_code,
            )
        self.main_window.present()
        if self.splash:
            self.splash.close()
            self.splash = None
        return False
