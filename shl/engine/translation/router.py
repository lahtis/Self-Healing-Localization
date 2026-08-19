"""
File: router.py — Intelligent routing logic for SHL translation ecosystem.
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description: Coordinates provider priorities, executes automated failover mechanisms,
             maintains service availability status, and interfaces with memory cache and registries.
             Includes strict input validation, empty string fixes, and global timeouts.
             Supports DeepL, Google, Papago, LibreTranslate, and MyMemory with .env auto-detection.
"""


import time
import logging
from typing import Optional, List, Dict, Any

from .provider_cache import load_cache
from shl.config.config import get_ttl
from .cache import TranslationCache
from .metadata import TranslationRequest, TranslationResult
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    RateLimitExceededError,
)

from .providers.microsoft import MicrosoftTranslatorAdapter
from .providers.mymemory import MyMemoryAdapter
from .providers.libretranslate import LibreTranslateAdapter
from .providers.libretranslate_mirrors import LibreTranslateMirrorManager
from .providers.libretranslate_registry import LibreTranslateRegistry

from .providers.deepl import DeepLAdapter
from .providers.googlev2 import GoogleV2Adapter
from .providers.google_registry import GoogleRegistry

from .providers.papago import PapagoAdapter
from .providers.papago_registry import PapagoRegistry

from .providers.microsoft_registry import MicrosoftServiceRegistry

from shl.utils.env_loader import get_env_value
from shl.config import get_config_value

logger = logging.getLogger(__name__)

_translation_cache = TranslationCache()
_mirror_manager = LibreTranslateMirrorManager()

_libre_registry = LibreTranslateRegistry()
_google_registry = GoogleRegistry()
_papago_registry = PapagoRegistry()

_ms_registry = MicrosoftServiceRegistry(
    ttl_seconds=get_config_value("microsoft_translator.ttl")
)


# ---------------------------------------------------------------------------
# PROVIDER PRIORITY
# ---------------------------------------------------------------------------

def get_provider_priority(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]:

    cache = load_cache()
    providers_cache = cache.get("providers", {})

    ms_langs = providers_cache.get("microsoft_translator", {})
    lt_langs = providers_cache.get("libretranslate", {})
    pg_langs = providers_cache.get("pagago", [])
    mm_langs = providers_cache.get("mymemory", [])

    providers: List[str] = []

    # Microsoft Translator (symmetrinen avainlogiikka)
    ms_key = microsoft_api_key or get_env_value("MICROSOFT_TRANSLATOR_KEY")
    if ms_key and _ms_registry.is_available():
        if source_lang.lower() in ms_langs and target_lang.lower() in ms_langs:
            providers.append("microsoft_translator")

    # DeepL
    deepl_key = deepl_key or get_env_value("DEEPL_API_KEY")
    if deepl_key:
        providers.append("deepl")

    # Google
    google_api_key = google_api_key or get_env_value("GOOGLE_API_KEY")
    if google_api_key:
        if _google_registry.is_pair_supported(source_lang, target_lang):
            providers.append("google")

    # Papago
    papago_client_id = papago_client_id or get_env_value("NAVER_CLIENT_ID")
    papago_client_secret = papago_client_secret or get_env_value("NAVER_CLIENT_SECRET")

    static_pg = (
        source_lang.lower() in pg_langs and
        target_lang.lower() in pg_langs
    )

    if papago_client_id and papago_client_secret:
        if _papago_registry.is_pair_supported(source_lang, target_lang, static_pg):
            providers.append("papago")

    # LibreTranslate
    if source_lang.lower() in lt_langs and target_lang.lower() in lt_langs:
        if _libre_registry.is_pair_supported(source_lang, target_lang):
            providers.append("libretranslate")

    # MyMemory
    if source_lang.lower() in mm_langs and target_lang.lower() in mm_langs:
        providers.append("mymemory")

    return providers


# ---------------------------------------------------------------------------
# BEST PROVIDER
# ---------------------------------------------------------------------------

def get_best_provider(
    target_lang: str,
    source_lang: str = "en",
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str:

    providers = get_provider_priority(
        target_lang,
        source_lang,
        deepl_key,
        google_api_key,
        papago_client_id,
        papago_client_secret,
        microsoft_api_key,
        request,
    )

    return providers[0] if providers else "mymemory"

def get_libretranslate_mirror_stats() -> Dict[str, Any]:
    """Get statistics about LibreTranslate mirrors."""
    return _mirror_manager.get_stats()

# ---------------------------------------------------------------------------
# CLEAR UNAVAILABLE CACHE
# ---------------------------------------------------------------------------

def clear_unavailable_cache() -> None:
    _mirror_manager.clear_blacklist()
    _libre_registry.clear_blacklist()
    _google_registry.clear_blacklist()
    _papago_registry.clear_blacklist()
    _ms_registry.clear()


# ---------------------------------------------------------------------------
# UNAVAILABLE CACHE STATS
# ---------------------------------------------------------------------------

def get_unavailable_cache_stats() -> Dict[str, Any]:
    return {
        "blacklisted_mirrors": len(_mirror_manager.blacklist),
        "blacklisted_google_pairs": len(_google_registry._unsupported_pairs_cache),
        "blacklisted_libre_pairs": len(_libre_registry._unsupported_pairs_cache),
        "blacklisted_papago_pairs": len(_papago_registry._unsupported_pairs_cache),
        "microsoft_unavailable": not _ms_registry.is_available(),
    }


# ---------------------------------------------------------------------------
# TRANSLATION EXECUTION
# ---------------------------------------------------------------------------

def translate_text_with_metadata(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> TranslationResult:

    if not text:
        return TranslationResult(
            translated_text=text,
            source="input_validation",
            request_metadata=request or TranslationRequest(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
            ),
        )

    if not isinstance(text, str):
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
            text, source_lang, target_lang, formality, context_type
        )
        if cached is not None:
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
        papago_client_id,
        papago_client_secret,
        microsoft_api_key,
        request,
    )

    ms_key = microsoft_api_key or get_env_value("MICROSOFT_TRANSLATOR_KEY")

    for service in order:
        if time.time() - start_time > total_timeout:
            break

        for attempt in range(max_retries):
            if time.time() - start_time > total_timeout:
                break

            try:
                translated = None

                if service == "microsoft_translator":
                    adapter = MicrosoftTranslatorAdapter(api_key=ms_key)
                    translated = adapter.translate(request)

                elif service == "deepl":
                    adapter = DeepLAdapter(api_key=deepl_key) if deepl_key else DeepLAdapter()
                    translated = adapter.translate(request)

                elif service == "google":
                    adapter = GoogleV2Adapter(
                        api_key=google_api_key,
                        backup_api_key=google_backup_api_key,
                    ) if google_api_key else GoogleV2Adapter()
                    translated = adapter.translate(request)

                elif service == "papago":
                    adapter = PapagoAdapter(
                        client_id=papago_client_id,
                        client_secret=papago_client_secret,
                    ) if papago_client_id and papago_client_secret else PapagoAdapter()
                    translated = adapter.translate(request)

                elif service == "libretranslate":
                    adapter = LibreTranslateAdapter(mirror_manager=_mirror_manager)
                    translated = adapter.translate(request)

                elif service == "mymemory":
                    adapter = MyMemoryAdapter(email=mymemory_email)
                    translated = adapter.translate(request)

                if translated is not None:
                    if use_cache:
                        _translation_cache.set(
                            text, translated, source_lang, target_lang, formality, context_type
                        )

                    return TranslationResult(
                        translated_text=translated,
                        source=service,
                        request_metadata=request,
                    )

            except LanguageNotSupportedError:
                if service == "google":
                    _google_registry.mark_pair_unsupported(source_lang, target_lang)
                elif service == "libretranslate":
                    _libre_registry.mark_pair_unsupported(source_lang, target_lang)
                elif service == "papago":
                    _papago_registry.mark_pair_unsupported(source_lang, target_lang)
                break

            except RateLimitExceededError:
                break

            except TranslationError:
                backoff = retry_delay * (attempt + 1)
                if (time.time() - start_time) + backoff > total_timeout:
                    break
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                continue

            except Exception:
                if service == "microsoft_translator":
                    _ms_registry.mark_unavailable()
                break

    raise ServiceUnavailableError(
        f"All translation services failed or timed out within {total_timeout}s."
    )


# ---------------------------------------------------------------------------
# RAW TRANSLATION WRAPPER
# ---------------------------------------------------------------------------

def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
    use_cache: bool = True,
    mymemory_email: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    request: Optional[TranslationRequest] = None,
) -> str:

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
            papago_client_id=papago_client_id,
            papago_client_secret=papago_client_secret,
            microsoft_api_key=microsoft_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            total_timeout=total_timeout,
            request=request,
        )
        return result.translated_text
    except Exception:
        return text

