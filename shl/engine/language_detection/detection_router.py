"""
File: detection_router.py — Policy-aware routing for SHL language detection.
Author: Tuomas Lähteenmäki
Version: 0.2.13
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
from shl.engine.errors import ErrorParser
from shl.engine.errors.providers import DETECTLANGUAGE

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
        available = _policy.get_available_detection_providers()

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
# POLICY PROVIDER NAME
# ---------------------------------------------------------------------------

def _get_policy_provider_name(
    provider_name: str,
) -> str:
    """
    Resolve a provider name to its canonical policy name.

    Provider names inside the router are normalized to lowercase,
    while policy configuration preserves its configured casing.
    """

    if _USE_POLICY and _policy is not None:
        config = _policy.get()
        providers = config.get("providers", {})

        for name in providers:
            if name.lower() == provider_name.lower():
                return name

    return provider_name


# ---------------------------------------------------------------------------
# PROVIDER TIMEOUT
# ---------------------------------------------------------------------------

def get_provider_timeout(
    provider_name: str,
) -> float:
    """Get provider timeout from policy manager or default."""

    if _USE_POLICY and _policy is not None:
        policy_name = _get_policy_provider_name(
            provider_name,
        )

        return _policy.get_timeout(
            policy_name,
            default=10.0,
        )

    return 10.0


# ---------------------------------------------------------------------------
# PROVIDER RETRY
# ---------------------------------------------------------------------------

def get_provider_retry(
    provider_name: str,
) -> int:
    """Get provider retry count from policy manager or default."""

    if _USE_POLICY and _policy is not None:
        policy_name = _get_policy_provider_name(
            provider_name,
        )

        return _policy.get_retry(
            policy_name,
            default=0,
        )

    return 0


# ---------------------------------------------------------------------------
# ERROR PARSER
# ---------------------------------------------------------------------------

def _get_error_parser(
    provider_name: str,
) -> ErrorParser:
    """Create an error parser using the provider error definition."""

    provider_name = provider_name.lower()

    if provider_name == "detectlanguage":
        return ErrorParser(
            provider=provider_name,
            config=DETECTLANGUAGE,
        )

    return ErrorParser(
        provider=provider_name,
    )


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
    Retry behavior is controlled by the provider policy.
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
            service,
        )

        retry_count = get_provider_retry(
            service,
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

        parser = _get_error_parser(
            service,
        )

        for attempt in range(
            retry_count + 1,
        ):
            if time.time() - start_time >= total_timeout:
                break

            try:
                adapter = _create_provider(
                    service,
                )

                logger.debug(
                    "Language detection using provider '%s' "
                    "(attempt %d/%d, timeout=%s).",
                    service,
                    attempt + 1,
                    retry_count + 1,
                    timeout,
                )

                # The current provider adapters use their own
                # network timeout. The calculated timeout is kept
                # here for router-level deadline handling.
                results = adapter.detect(
                    text,
                )

                if results:
                    return results

            except Exception as exception:
                http_status = getattr(
                    exception,
                    "code",
                    None,
                )

                if not isinstance(
                    http_status,
                    int,
                ):
                    http_status = None

                normalized_error = parser.parse(
                    exception=exception,
                    http_status=http_status,
                )

                logger.warning(
                    "Language detection provider '%s' failed "
                    "(attempt %d/%d): %s",
                    service,
                    attempt + 1,
                    retry_count + 1,
                    normalized_error,
                )

                if (
                    normalized_error.retryable
                    and attempt < retry_count
                ):
                    logger.info(
                        "Retrying language detection provider '%s' "
                        "(retry %d/%d).",
                        service,
                        attempt + 1,
                        retry_count,
                    )
                    continue

                break

    raise RuntimeError(
        "All language detection providers failed "
        "or timed out."
    )
