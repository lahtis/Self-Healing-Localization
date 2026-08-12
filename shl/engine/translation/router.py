"""
File: router.py — Intelligent routing logic for SHL translation ecosystem.
Author: Tuomas Lähteenmäki
Version: 0.2.1
License: MIT
Description: Coordinates provider priorities, executes automated failover mechanisms,
             maintains service availability status, and interfaces with memory cache and registries.
             Includes strict input validation, empty string fixes, and global timeouts.
"""

import time
import logging
from typing import Optional, List, Dict, Any

from .cache import TranslationCache
from .metadata import TranslationRequest, TranslationResult
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    RateLimitExceededError,
)
from .providers.mymemory import MyMemoryAdapter
from .providers.libretranslate import (
    LibreTranslateAdapter,
)

from .providers.libretranslate_mirrors import (
    LibreTranslateMirrorManager,
)

from .providers.libretranslate_registry import LibreTranslateRegistry
from .providers.deepl import DeepLAdapter
from .providers.googlev2 import GoogleV2Adapter
from .providers.google_registry import GoogleRegistry

logger = logging.getLogger(__name__)

_translation_cache = TranslationCache()
_mirror_manager = LibreTranslateMirrorManager()

# Registry-instanssit kieliparien tarkistukseen ja oppimiseen
_libre_registry = LibreTranslateRegistry()
_google_registry = GoogleRegistry()


def get_provider_priority(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]:
    """Determine the prioritized order of provider adapters based on constraints and configuration."""
    providers = []

    # Premium services high-priority check
    if deepl_key:
        providers.append("deepl")

    # Tarkistetaan Google-rekisteristä ennen priorisointia
    if google_api_key and _google_registry.is_pair_supported(
        source_lang, target_lang
    ):
        providers.append("google")

    # Open / Community services
    if _libre_registry.is_pair_supported(source_lang, target_lang):
        providers.append("libretranslate")

    providers.append("mymemory")

    return providers


def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str:
    """Get the highest priority provider for the given configuration."""
    providers = get_provider_priority(
        target_lang,
        source_lang,
        deepl_key,
        google_api_key,
        request,
    )

    return providers[0] if providers else "mymemory"


def get_libretranslate_mirror_stats() -> Dict[str, Any]:
    """Get statistics about LibreTranslate mirrors."""
    return _mirror_manager.get_stats()


def get_all_supported_languages() -> List[str]:
    """Return a combined list of supported ISO language codes across all providers."""
    return ["en", "fi", "sv", "de", "fr", "es", "it", "ru", "zh", "ja"]


def clear_unavailable_cache() -> None:
    """Clear internal tracking of blacklisted/unavailable providers and language registries."""
    _mirror_manager.clear_blacklist()
    _libre_registry.clear_blacklist()
    _google_registry.clear_blacklist()


def get_unavailable_cache_stats() -> Dict[str, Any]:
    """Retrieve statistics regarding currently unavailable endpoints and blacklisted language pairs."""
    return {
        "blacklisted_mirrors": len(_mirror_manager.blacklist),
        "blacklisted_google_pairs": len(
            _google_registry._unsupported_pairs_cache
        ),
        "blacklisted_libre_pairs": len(
            _libre_registry._unsupported_pairs_cache
        ),
    }


def translate_text_with_metadata(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> TranslationResult:
    """
    Primary routing execution entrypoint. Returns a detailed TranslationResult object.
    Handles automated fallback paths, retries, registries learning, and global execution time limits.
    """

    if not text:
        return TranslationResult(
            translated_text=text,
            source="input_validation",
            request_metadata=request
            or TranslationRequest(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
            ),
        )

    if not isinstance(text, str):
        logger.warning(
            f"translate_text_with_metadata: Invalid input type {type(text)}, "
            "forcing str conversion."
        )
        text = str(text)

    if request is None:
        request = TranslationRequest(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )

    formality = request.formality
    context_type = request.context_type
    start_time = time.time()

    if use_cache:
        cached = _translation_cache.get(
            text,
            source_lang,
            target_lang,
            formality,
            context_type,
        )

        if cached is not None:
            logger.info("Translation retrieved from cache")
            return TranslationResult(
                translated_text=cached,
                source="cache",
                request_metadata=request,
            )

    order = get_provider_priority(
        target_lang,
        source_lang,
        deepl_key,
        google_api_key,
        request,
    )

    logger.info(
        f"Selected priority path for "
        f"{source_lang}->{target_lang}: {order}"
    )

    for service in order:
        if time.time() - start_time > total_timeout:
            logger.error(
                f"Global timeout ({total_timeout}s) exceeded before "
                f"attempting provider '{service}'."
            )
            break

        for attempt in range(max_retries):
            if time.time() - start_time > total_timeout:
                logger.error(
                    f"Global timeout ({total_timeout}s) exceeded during "
                    f"attempt {attempt + 1} for '{service}'."
                )
                break

            try:
                translated: Optional[str] = None

                if service == "deepl" and deepl_key:
                    adapter = DeepLAdapter(api_key=deepl_key)
                    translated = adapter.translate(request)

                elif service == "google" and google_api_key:
                    adapter = GoogleV2Adapter(
                        api_key=google_api_key,
                        backup_api_key=google_backup_api_key,
                    )
                    translated = adapter.translate(request)

                elif service == "libretranslate":
                    adapter = LibreTranslateAdapter(
                        mirror_manager=_mirror_manager
                    )
                    translated = adapter.translate(request)

                elif service == "mymemory":
                    adapter = MyMemoryAdapter(
                        email=mymemory_email
                    )
                    translated = adapter.translate(request)

                if translated is not None:
                    logger.info(
                        f"Successfully translated '{text[:20]}...' "
                        f"({source_lang}->{target_lang}) using provider: "
                        f"'{service}'"
                    )

                    if use_cache:
                        _translation_cache.set(
                            text,
                            translated,
                            source_lang,
                            target_lang,
                            formality,
                            context_type,
                        )

                    return TranslationResult(
                        translated_text=translated,
                        source=service,
                        request_metadata=request,
                    )

            except LanguageNotSupportedError as e:
                logger.warning(
                    f"Provider '{service}' does not support pair "
                    f"{source_lang}->{target_lang}. "
                    "Updating registry blacklist."
                )

                # Opetetaan rekisterille, että tämä kielipari ei ole tuettu
                if service == "google":
                    _google_registry.mark_pair_unsupported(
                        source_lang,
                        target_lang,
                    )
                elif service == "libretranslate":
                    _libre_registry.mark_pair_unsupported(
                        source_lang,
                        target_lang,
                    )

                break

            except RateLimitExceededError as e:
                logger.warning(
                    f"Provider '{service}' hit rate limit: {e}. "
                    "Shifting to fallback."
                )
                break

            except TranslationError as e:
                backoff = retry_delay * (attempt + 1)

                logger.warning(
                    f"Provider '{service}' failed attempt "
                    f"{attempt + 1}/{max_retries}: {e}"
                )

                if (time.time() - start_time) + backoff > total_timeout:
                    logger.error(
                        "Next retry delay would exceed global timeout "
                        "limit. Skipping retry."
                    )
                    break

                if attempt < max_retries - 1:
                    time.sleep(backoff)

                continue

            except Exception as e:
                logger.error(
                    f"Unexpected error with provider '{service}': {e}",
                    exc_info=True,
                )
                break

    raise ServiceUnavailableError(
        f"All available translation services failed or timed out "
        f"within {total_timeout}s."
    )


def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> str:
    """
    Convenience wrapper returning raw translated text string.
    Returns original string as fallback on total failure to avoid breaking calling application.
    """

    try:
        result = translate_text_with_metadata(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang,
            use_cache=use_cache,
            mymemory_email=mymemory_email,
            deepl_key=deepl_key,
            google_api_key=google_api_key,
            google_backup_api_key=google_backup_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            total_timeout=total_timeout,
            request=request,
        )

        return result.translated_text

    except ServiceUnavailableError as e:
        logger.error(
            f"translate_text wrapper: {e} "
            "Returning original text as robust fallback."
        )
        return text

    except Exception as e:
        logger.error(
            f"Unexpected failure in routing wrapper: {e}. "
            "Returning original text."
        )
        return text
