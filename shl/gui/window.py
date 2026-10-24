"""Main window for SHL 2.0."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from shl.gui.localizer import GuiLocalizer


class MainWindow(Gtk.ApplicationWindow):
    """Main SHL window showing translation state."""

    def __init__(self, application, localizer: GuiLocalizer,
                 app_name: str, lang_code: str):
        super().__init__(application=application, title="SHL")
        self.localizer = localizer
        self.app_name = app_name
        self.lang_code = lang_code
        self._ = localizer.L

        self.set_default_size(800, 600)

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda b: self.close())
        header.pack_end(close_button)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        self.set_child(box)

        title = Gtk.Label(label="SHL 2.0")
        title.add_css_class("title-1")
        box.append(title)

        info = Gtk.Label(
            label=f"Application: {app_name}\n"
                  f"Language: {lang_code}\n"
                  f"Keys loaded: {len(localizer)}"
        )
        info.set_wrap(True)
        info.set_selectable(True)
        box.append(info)

        if len(localizer) > 0:
            sample = "\n".join(
                f"{k} = {v}" for k, v in list(localizer.texts.items())[:20]
            )
            sample_label = Gtk.Label(label=sample)
            sample_label.set_wrap(True)
            sample_label.set_selectable(True)
            box.append(sample_label)
        else:
            box.append(Gtk.Label(label="No translations loaded yet."))
