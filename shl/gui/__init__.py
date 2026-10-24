"""SHL 2.0 GUI layer – splash, preload generator, UI adapters."""
from shl.gui.paths import Paths
from shl.gui.app_config import AppConfig
from shl.gui.localizer import GuiLocalizer
from shl.gui.preload import preload

__all__ = [
    "Paths",
    "AppConfig",
    "GuiLocalizer",
    "preload",
]
