"""CLI adapter for SHL 2.0 – consumes PreloadEvent stream."""
import sys
from pathlib import Path

from shl.gui.app_config import AppConfig
from shl.gui.paths import Paths
from shl.gui.preload import preload


def run_cli(argv=None):
    """Run preload with progress output to stdout."""
    if argv is None:
        argv = sys.argv

    args = [a for a in argv[1:] if not a.startswith("-")]
    app_name = args[0] if len(args) > 0 else "shl-gui"
    lang_code = args[1] if len(args) > 1 else "en"
    source_path = Path(args[2]) if len(args) > 2 else Path.cwd()

    Paths.ensure_all(app_name)
    config = AppConfig(app_name)

    print(f"App: {app_name}")
    print(f"Lang: {lang_code}")
    print(f"Source: {source_path}")
    print("-" * 60)

    for event in preload(
        source_path=source_path,
        app_name=app_name,
        lang_code=lang_code,
        base_lang=config.base_lang,
    ):
        fraction = event.phase_fraction
        if event.kind == "translate" and event.total > 0:
            fraction = event.key_fraction
        bar = "#" * int(fraction * 30) + "-" * (30 - int(fraction * 30))
        print(f"[{bar}] {fraction * 100:3.0f}%  {event.message}")

    print("-" * 60)
    print("Done.")
    return 0
