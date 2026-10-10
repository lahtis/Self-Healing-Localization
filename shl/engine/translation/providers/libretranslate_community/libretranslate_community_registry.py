"""
File: shl/engine/translation/providers/libretranslate_community/libretranslate_community_registry.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Manages LibreTranslate Community language validation and runtime
    learning for unsupported language pairs.

    Supported languages are loaded from the shared provider language
    cache. No network requests are performed by this registry.

    Runtime unsupported-pair blacklist TTL is controlled through the
    central SHL configuration.

    This module performs no HTTP calls. It only reads a local cache
    file and tracks rejected pairs at runtime.
"""

import json
import logging
import time
from pathlib import Path

from shl.config import get_ttl


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[5]
LANGUAGE_CACHE_FILE = PROJECT_ROOT / ".languages_cache.json"


class LibreTranslateCommunityRegistry:
    """Language support validation and runtime pair blacklisting for
    LibreTranslate Community.

    Supported languages are loaded from the shared provider language
    cache. The registry never performs network requests.

    The runtime unsupported-pair blacklist prevents repeated API calls
    for language pairs that LibreTranslate Community has previously
    rejected.
    """

    def __init__(self):
        # Runtime blacklist:
        # (source, target) -> expiry timestamp
        self._unsupported_pairs_cache: dict[
            tuple[str, str], float
        ] = {}

        # Load blacklist TTL from central SHL configuration.
        configured_ttl = get_ttl(
            "libretranslate_community",
            86400,
        )

        try:
            self.cache_ttl = float(configured_ttl)
        except (TypeError, ValueError):
            self.cache_ttl = 86400.0

        # Load provider languages from the shared cache.
        self.supported_languages = self._load_supported_languages()

        logger.debug(
            "LibreTranslate Community registry loaded "
            "%d supported languages "
            "(pair blacklist TTL: %.1f seconds)",
            len(self.supported_languages),
            self.cache_ttl,
        )

    def _load_supported_languages(self) -> frozenset[str]:
        """Load LibreTranslate Community supported language codes from
        the shared provider language cache.

        Expected cache structure::

            {
                "providers": {
                    "libretranslate_community": ["en", "fi", "de", ...]
                }
            }

        Returns:
            frozenset[str]: Normalized language codes. Empty set on any
            read, parse, or structure error (fail-closed).
        """

        try:
            with LANGUAGE_CACHE_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except FileNotFoundError:
            logger.warning(
                "LibreTranslate Community language cache not found: %s",
                LANGUAGE_CACHE_FILE,
            )
            return frozenset()

        except json.JSONDecodeError:
            logger.warning(
                "LibreTranslate Community language cache contains "
                "invalid JSON: %s",
                LANGUAGE_CACHE_FILE,
            )
            return frozenset()

        except OSError as exc:
            logger.warning(
                "Unable to read LibreTranslate Community language "
                "cache: %s",
                exc,
            )
            return frozenset()

        providers = data.get("providers", {})

        if not isinstance(providers, dict):
            logger.warning(
                "Invalid provider section in language cache."
            )
            return frozenset()

        languages = providers.get(
            "libretranslate_community",
            [],
        )

        if not isinstance(languages, list):
            logger.warning(
                "Invalid LibreTranslate Community language cache "
                "structure."
            )
            return frozenset()

        return frozenset(
            code.strip().lower()
            for code in languages
            if isinstance(code, str) and code.strip()
        )

    def is_pair_supported(
        self,
        source_lang: str,
        target_lang: str,
    ) -> bool:
        """Check whether a LibreTranslate Community language pair is
        currently supported.

        First checks the runtime unsupported-pair blacklist. If the
        pair is not blacklisted, both language codes are checked
        against the provider language cache.

        Args:
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            True if both languages are available and the pair is not
            currently blacklisted.
        """

        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        pair = (src, tgt)
        now = time.time()

        # Check the runtime blacklist.
        if pair in self._unsupported_pairs_cache:
            expiry = self._unsupported_pairs_cache[pair]

            if now < expiry:
                logger.debug(
                    "LibreTranslate Community pair %s is currently "
                    "blacklisted.",
                    pair,
                )
                return False

            # TTL expired; allow the pair to be tested again.
            del self._unsupported_pairs_cache[pair]

        # Check the provider language cache.
        return (
            src in self.supported_languages
            and tgt in self.supported_languages
        )

    def mark_pair_unsupported(
        self,
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Temporarily blacklist an unsupported LibreTranslate
        Community language pair.

        The blacklist duration is controlled by the central SHL
        configuration under ``ttl.libretranslate_community``.
        """

        pair = (
            source_lang.strip().lower(),
            target_lang.strip().lower(),
        )

        self._unsupported_pairs_cache[pair] = (
            time.time() + self.cache_ttl
        )

        logger.warning(
            "Blacklisted LibreTranslate Community language pair "
            "%s for %.1f seconds due to API error.",
            pair,
            self.cache_ttl,
        )

    def clear_blacklist(self) -> None:
        """Clear all runtime unsupported language pairs."""
        self._unsupported_pairs_cache.clear()
