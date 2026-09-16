"""
File: detection_router.py — Policy-aware routing for SHL language detection.
Author: Tuomas Lähteenmäki
Version: 0.2.11
License: MIT
"""

import logging
import time
from typing import List, Optional

from .provider_cache import load_cache

from .providers.base import (
    LanguageDetectionResult,
)

from .providers.detect_language import (
    DetectLanguageAdapter,
)

from shl.config.policy_manager import ConfigManager
from shl.utils.env_loader import get_env_value


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POLICY MANAGER INITIALIZATION
# ---------------------------------------------------------------------------

try:
    _policy = ConfigManager()
    _USE_POLICY = True
    print(
        f"[Detection Router] PolicyManager loaded from "
        f"{_policy.path}"
    )
except Exception as error:
    _USE_POLICY = False
    _policy = None
    print(
        f"[Detection Router] PolicyManager failed to load: "
        f"{error}"
    )


# ---------------------------------------------------------------------------
# PROVIDER CACHE
# ---------------------------------------------------------------------------

_PROVIDER_CACHE = load_cache()


# ---------------------------------------------------------------------------
# PROVIDER PRIORITY
# ---------------------------------------------------------------------------

def get_provider_priority(
    source_lang: Optional[str] = None,
) -> List[str]:
    """
    Return language detection providers in priority order.

    When PolicyManager is available, provider order is taken from policy.
    Otherwise, providers are selected from the language detection cache.
    """

    if _USE_POLICY and _policy is not None:
        available = _policy.get_available_providers()

        if available:
            return [
                name.lower()
                for name in available
            ]

    providers_cache = _PROVIDER_CACHE.get(
        "providers",
        {},
    )

    providers = []

    for provider_name, languages in providers_cache.items():
        if not languages:
            continue

        if source_lang:
            normalized_source = source_lang.lower()

            if isinstance(languages, dict):
                if normalized_source not in {
                    code.lower()
                    for code in languages
                }:
                    continue

            elif isinstance(languages, list):
                supported = {
                    str(code).lower()
                    for code in languages
                }

                if normalized_source not in supported:
                    continue

        providers.append(
            provider_name.lower()
        )

    return providers


# ---------------------------------------------------------------------------
# PROVIDER TIMEOUT
# ---------------------------------------------------------------------------

def get_provider_timeout(
    provider_name: str,
) -> float:
    """Get provider timeout from policy manager or default."""

    if _USE_POLICY and _policy is not None:
        return _policy.get_timeout(
            provider_name,
            default=10.0,
        )

    return 10.0


# ---------------------------------------------------------------------------
# PROVIDER FACTORY
# ---------------------------------------------------------------------------

def _create_provider(
    provider_name: str,
):
    """
    Create a language detection provider adapter.

    Provider-specific configuration remains inside the adapter.
    """

    if provider_name == "detectlanguage":
        return DetectLanguageAdapter()

    raise ValueError(
        f"Unsupported language detection provider: "
        f"{provider_name}"
    )


# ---------------------------------------------------------------------------
# LANGUAGE DETECTION
# ---------------------------------------------------------------------------

def detect_language(
    text: str,
    source_lang: Optional[str] = None,
    total_timeout: float = 30.0,
) -> List[LanguageDetectionResult]:
    """
    Detect the language of the supplied text.

    Providers are attempted in policy or cache priority order.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "Text must be a non-empty string."
        )

    order = get_provider_priority(
        source_lang=source_lang,
    )

    logger.info(
        "Language detection provider order: %s",
        order,
    )

    start_time = time.time()

    for service in order:
        if time.time() - start_time >= total_timeout:
            break

        provider_timeout = get_provider_timeout(
            service
        )

        remaining = total_timeout - (
            time.time() - start_time
        )

        if remaining <= 0:
            break

        timeout = min(
            provider_timeout,
            remaining,
        )

        try:
            adapter = _create_provider(service)

            logger.debug(
                "Language detection using provider '%s'.",
                service,
            )

            # The current provider adapters use their own
            # network timeout. The calculated timeout is kept
            # here for router-level deadline handling.
            results = adapter.detect(text)

            if results:
                return results

        except Exception as error:
            logger.warning(
                "Language detection provider '%s' failed: %s",
                service,
                error,
            )

            continue

    raise RuntimeError(
        "All language detection providers failed "
        "or timed out."
    )
