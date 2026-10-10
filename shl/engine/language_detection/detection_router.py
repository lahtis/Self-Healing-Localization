"""
File: shl/engine/language_detection/detection_router.py — Policy-aware
routing for SHL language detection.
Author: Tuomas Lähteenmäki
Version: 0.3.1
License: MIT
"""

import logging
import time

from .provider_cache import load_cache

from .providers.base import (
    LanguageDetectionProvider,
    LanguageDetectionResult,
)

from .providers.detect_language import (
    DetectLanguageAdapter,
)

from .providers.deepl import (
    DeepLDetectionAdapter,
)

from shl.config.policy_manager import ConfigManager
from shl.engine.errors import ErrorParser
from shl.engine.errors.providers import DEEPL, DETECTLANGUAGE

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POLICY MANAGER INITIALIZATION
# ---------------------------------------------------------------------------

_policy: ConfigManager | None

try:
    _policy = ConfigManager()
    _USE_POLICY = True
    logger.info(
        "PolicyManager loaded from %s",
        _policy.path,
    )
except Exception as error:
    _USE_POLICY = False
    _policy = None
    logger.warning(
        "PolicyManager failed to load: %s",
        error,
    )


# ---------------------------------------------------------------------------
# PROVIDER CACHE
# ---------------------------------------------------------------------------

_PROVIDER_CACHE = load_cache()


# ---------------------------------------------------------------------------
# PROVIDER PRIORITY
# ---------------------------------------------------------------------------

def get_provider_priority(
    source_lang: str | None = None,
) -> list[str]:
    """Return language detection providers in priority order.

    Policy takes precedence. Providers are expected to be filtered by
    `detection_enabled` and ordered by `detection_priority` inside
    PolicyManager. Providers whose `detection_priority` is null are
    excluded.
    """

    if _USE_POLICY and _policy is not None:
        available = _policy.get_available_detection_providers()

        if available:
            return [name.lower() for name in available]

    # Fallback: infer from the static provider cache when policy
    # is unavailable.
    providers_cache = _PROVIDER_CACHE.get("providers", {})

    providers = []

    for provider_name, languages in providers_cache.items():
        if not languages:
            continue

        if source_lang:
            normalized_source = source_lang.lower()

            if isinstance(languages, dict):
                if normalized_source not in {
                    code.lower() for code in languages
                }:
                    continue

            elif isinstance(languages, list):
                supported = {
                    str(code).lower() for code in languages
                }

                if normalized_source not in supported:
                    continue

        providers.append(provider_name.lower())

    return providers


# ---------------------------------------------------------------------------
# POLICY PROVIDER NAME
# ---------------------------------------------------------------------------

def _get_policy_provider_name(provider_name: str) -> str:
    """Resolve a provider name to its canonical policy name."""

    if _USE_POLICY and _policy is not None:
        config = _policy.get()
        providers = config.get("providers", {})

        if not isinstance(providers, dict):
            return provider_name

        for name in providers:
            if name.lower() == provider_name.lower():
                return str(name)

    return provider_name


# ---------------------------------------------------------------------------
# PROVIDER TIMEOUT
# ---------------------------------------------------------------------------

def get_provider_timeout(provider_name: str) -> float:
    """Get provider timeout (seconds) from policy or default."""

    if _USE_POLICY and _policy is not None:
        policy_name = _get_policy_provider_name(provider_name)
        return _policy.get_timeout(policy_name, default=10.0)

    return 10.0


# ---------------------------------------------------------------------------
# PROVIDER RETRY
# ---------------------------------------------------------------------------

def get_provider_retry(provider_name: str) -> int:
    """Get provider retry count from policy or default."""

    if _USE_POLICY and _policy is not None:
        policy_name = _get_policy_provider_name(provider_name)
        value = _policy.get_retry(policy_name, default=0)
        if isinstance(value, int) and value >= 0:
            return value
        return 0

    return 0


def get_provider_retry_delay(provider_name: str) -> float:
    """Get provider retry delay (seconds) from policy or default."""

    if _USE_POLICY and _policy is not None:
        policy_name = _get_policy_provider_name(provider_name)
        value = _policy.get_retry_delay(policy_name, default=0.0)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        return 0.0

    return 0.0


# ---------------------------------------------------------------------------
# ERROR PARSER
# ---------------------------------------------------------------------------

def _get_error_parser(provider_name: str) -> ErrorParser:
    """Create an error parser using the provider error definition."""

    provider_name = provider_name.lower()

    if provider_name == "detectlanguage":
        return ErrorParser(
            provider=provider_name,
            config=DETECTLANGUAGE,
        )

    if provider_name == "deepl":
        return ErrorParser(
            provider=provider_name,
            config=DEEPL,
        )

    return ErrorParser(provider=provider_name)


# ---------------------------------------------------------------------------
# PROVIDER FACTORY
# ---------------------------------------------------------------------------

def _create_provider(provider_name: str) -> LanguageDetectionProvider:
    """Create a language detection provider adapter."""

    if provider_name == "detectlanguage":
        return DetectLanguageAdapter()

    if provider_name == "deepl":
        return DeepLDetectionAdapter()

    raise ValueError(
        f"Unsupported language detection provider: {provider_name}"
    )


# ---------------------------------------------------------------------------
# LANGUAGE DETECTION
# ---------------------------------------------------------------------------

def detect_language(
    text: str,
    source_lang: str | None = None,
    total_timeout: float = 30.0,
) -> list[LanguageDetectionResult]:
    """
    Detect the language of the supplied text.

    Providers are attempted in policy or cache priority order.
    Timeout, retry count, and retry delay come from the provider
    policy. Retries happen only on retryable errors; empty results
    move on to the next provider immediately.

    Args:
        text: Text to detect.
        source_lang: Optional source language hint. Some providers
            (e.g. DeepL) require it to construct a valid request.
        total_timeout: Wall-clock budget across all providers and
            retries.

    Raises:
        ValueError: if text is not a non-empty string.
        RuntimeError: if no detection providers are enabled, or if
            every provider fails before any returns a result.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text must be a non-empty string.")

    order = get_provider_priority(source_lang=source_lang)

    # Distinguish "no providers configured" from "all providers
    # failed". The generic error at the end is misleading when the
    # policy has no detection providers enabled at all.
    if not order:
        raise RuntimeError(
            "No language detection providers are enabled. "
            "Set `detection_enabled: true` on at least one provider "
            "in shl-policy-config.json."
        )

    logger.info(
        "Language detection provider order: %s",
        order,
    )

    start_time = time.time()

    for service in order:
        if time.time() - start_time >= total_timeout:
            break

        provider_timeout = get_provider_timeout(service)
        retry_count = get_provider_retry(service)
        retry_delay = get_provider_retry_delay(service)

        remaining = total_timeout - (time.time() - start_time)
        if remaining <= 0:
            break

        timeout = min(provider_timeout, remaining)

        parser = _get_error_parser(service)

        # Create the adapter once per provider — construction failures
        # are not retryable.
        try:
            adapter = _create_provider(service)
        except Exception as exception:
            logger.warning(
                "Could not instantiate language detection provider "
                "'%s': %s",
                service,
                exception,
            )
            continue

        for attempt in range(retry_count + 1):
            if time.time() - start_time >= total_timeout:
                break

            try:
                logger.debug(
                    "Language detection using provider '%s' "
                    "(attempt %d/%d, timeout=%s).",
                    service,
                    attempt + 1,
                    retry_count + 1,
                    timeout,
                )

                results = adapter.detect(
                    text,
                    source_lang=source_lang,
                    timeout=timeout,
                )

                if results:
                    return results

                # Empty result = the provider answered but found no
                # language. This is not a transient failure, so do
                # not retry — move on to the next provider.
                logger.debug(
                    "Provider '%s' returned no detections; "
                    "trying next provider.",
                    service,
                )
                break

            except Exception as exception:
                # Broad on purpose: a provider failure of any kind
                # must not crash the router. Known transport and
                # HTTP errors are normalized by the parser.
                http_status = getattr(exception, "status_code", None)
                if not isinstance(http_status, int):
                    http_status = getattr(exception, "code", None)
                if not isinstance(http_status, int):
                    http_status = None

                normalized_error = parser.parse(
                    exception=exception,
                    http_status=http_status,
                )

                if normalized_error is None:
                    logger.warning(
                        "Language detection provider '%s' failed "
                        "(attempt %d/%d): unparsed exception %s",
                        service,
                        attempt + 1,
                        retry_count + 1,
                        type(exception).__name__,
                    )
                    break

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
                    if retry_delay > 0:
                        time.sleep(retry_delay)

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
        "All language detection providers failed or timed out."
    )
