"""
File: shl/engine/preload.py
Author: Tuomas Lähteenmäki
Version: 0.1.0
License: MIT
Description:
    Progress events for engine preloading.

    The preload generator yields PreloadEvent instances while the
    engine loads GLFM, locale files, and optionally translates
    missing keys. Callers (UI, CLI, splash screens) consume the
    events and decide how to display them.

    The engine does not render anything. It only reports what is
    happening and how far it has progressed.

    Event kinds, in the order they are emitted:

        glfm        GLFM database is being loaded
        language    A locale file is being loaded
        translate   Missing keys are being translated
        ready       All requested work is complete

    Every event carries both phase progress (done/total) and key
    progress (translated/missing) so a caller can choose which one
    to display.
"""

from dataclasses import dataclass


# Event kinds. These are stable strings; callers may compare against
# them directly.
KIND_GLFM = "glfm"
KIND_SCAN = "scan"
KIND_LANGUAGE = "language"
KIND_TRANSLATE = "translate"
KIND_READY = "ready"


@dataclass(frozen=True)
class PreloadEvent:
    """One progress event emitted by LocalizationEngine.preload().

    kind:
        One of KIND_GLFM, KIND_LANGUAGE, KIND_TRANSLATE, KIND_READY.

    done, total:
        Phase progress. Counts completed steps, not keys. A caller
        that wants a coarse progress bar uses done/total.

    message:
        Human-readable description. Intended for display as-is.

    translated, missing:
        Key progress for the active language. translated + missing
        equals the total number of keys considered. A caller that
        wants a fine-grained progress bar uses translated/(translated+missing).

    current_key:
        The key currently being translated, or "" when not in the
        translate phase.
    """

    kind: str
    done: int
    total: int
    message: str
    translated: int = 0
    missing: int = 0
    current_key: str = ""

    @property
    def key_total(self) -> int:
        """Total number of keys considered (translated + missing)."""
        return self.translated + self.missing

    @property
    def phase_fraction(self) -> float:
        """Phase progress as 0.0..1.0. Safe when total is 0."""
        if self.total <= 0:
            return 1.0
        return min(1.0, self.done / self.total)

    @property
    def key_fraction(self) -> float:
        """Key progress as 0.0..1.0. Safe when there are no keys."""
        if self.key_total <= 0:
            return 1.0
        return min(1.0, self.translated / self.key_total)
