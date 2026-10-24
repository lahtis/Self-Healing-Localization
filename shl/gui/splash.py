"""Splash window for SHL 2.0."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class SplashWindow(Gtk.Window):
    """Borderless splash with progress bar and status text."""

    def __init__(self, application):
        super().__init__(application=application)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(460, 240)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(32)
        box.set_margin_end(32)
        self.set_child(box)

        title = Gtk.Label(label="SHL")
        title.add_css_class("title-1")
        box.append(title)

        subtitle = Gtk.Label(label="Translating UI...")
        box.append(subtitle)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_fraction(0.0)
        box.append(self.progress)

        self.status = Gtk.Label(label="Starting up...")
        self.status.set_wrap(True)
        box.append(self.status)

        spinner = Gtk.Spinner()
        spinner.start()
        box.append(spinner)

    def set_status(self, message: str, fraction: float = None):
        self.status.set_text(message)
        if fraction is not None:
            self.progress.set_fraction(max(0.0, min(1.0, fraction)))
