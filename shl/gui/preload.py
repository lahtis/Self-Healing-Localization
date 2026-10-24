"""Preload generator for SHL 2.0.

Scans source code, translates missing keys, yields PreloadEvent
instances. UI adapters consume the event stream and display
progress however they choose.

This module is UI-agnostic. It does not import GTK, Flet or any
other GUI toolkit.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Iterator

from shl.engine.translation import translate_text
from shl.engine.preload import (
    PreloadEvent,
    KIND_SCAN,
    KIND_LANGUAGE,
    KIND_TRANSLATE,
    KIND_READY,
)
from shl.extract.scanner import scan_tree, merge_keys
from shl.gui.paths import Paths

logger = logging.getLogger(__name__)


def _load_json(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if v is not None}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return {}


def _save_json(path: Path, data: Dict[str, str]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
        tmp.replace(path)
        return True
    except OSError as exc:
        logger.error("Failed to save %s: %s", path, exc)
        return False


def preload(
    source_path: Path,
    app_name: str,
    lang_code: str,
    base_lang: str = "en",
    use_translation: bool = True,
) -> Iterator[PreloadEvent]:
    """Scan source, translate missing keys, yield progress events.

    Steps:
        1. Scan all .py files under source_path for translation keys.
        2. Load existing locales/<lang_code>.json.
        3. Determine which keys are missing.
        4. Translate missing keys one by one.
        5. Save the merged result once, at the end.

    Every step yields PreloadEvent so the caller can display progress.
    """
    Paths.ensure_all(app_name)
    lang_file = Paths.app_lang_file(app_name, lang_code)
    source_path = Path(source_path)

    # ---------- Step 1: scan ----------
    yield PreloadEvent(
        kind=KIND_SCAN,
        done=0,
        total=1,
        message="Scanning source files...",
    )

    scan_results = list(scan_tree(source_path))
    keys = merge_keys(scan_results)

    yield PreloadEvent(
        kind=KIND_SCAN,
        done=1,
        total=1,
        message=f"Found {len(keys)} translation keys",
        translated=0,
        missing=len(keys),
    )

    # ---------- Step 2: load existing ----------
    existing = _load_json(lang_file)
    missing = {k: v for k, v in keys.items() if k not in existing}

    yield PreloadEvent(
        kind=KIND_LANGUAGE,
        done=0,
        total=1,
        message=f"{len(existing)} existing, {len(missing)} missing",
        translated=len(existing),
        missing=len(missing),
    )

    # ---------- Step 3: translate missing ----------
    total = len(missing)
    translated_count = 0
    failed_count = 0

    for i, (key, default) in enumerate(missing.items()):
        source_text = default or key
        translated_value = source_text

        if use_translation and lang_code != base_lang and source_text:
            try:
                result = translate_text(
                    text=source_text,
                    target_lang=lang_code,
                    source_lang=base_lang,
                )
                if result:
                    translated_value = result
            except Exception as exc:
                logger.warning(
                    "Translation failed for key %r: %s", key, exc
                )
                failed_count += 1

        existing[key] = translated_value
        translated_count += 1

        yield PreloadEvent(
            kind=KIND_TRANSLATE,
            done=i + 1,
            total=total,
            message=f"Translating {i + 1}/{total}",
            translated=translated_count,
            missing=total - (i + 1),
            current_key=key,
        )

    # ---------- Step 4: save ----------
    saved = _save_json(lang_file, existing)

    if saved:
        message = f"Saved {len(existing)} keys to {lang_file.name}"
    else:
        message = f"Failed to save {lang_file.name}"

    if failed_count:
        message += f" ({failed_count} translations failed)"

    yield PreloadEvent(
        kind=KIND_READY,
        done=1,
        total=1,
        message=message,
        translated=len(existing),
        missing=0,
    )
