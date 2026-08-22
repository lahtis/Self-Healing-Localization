"""
File: router.py — Policy-aware routing for SHL translation ecosystem.
Author: Tuomas Lähteenmäki
Version: 0.2.5-casefix
License: MIT
"""


import time
import logging
from typing import Optional, List, Dict, Any

from .provider_cache import load_cache
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

from shl.config.policy_manager import ConfigManager
from shl.utils.env_loader import get_env_value
from shl.config import get_config_value

# ---------------------------------------------------------------------------
# POLICY MANAGER INITIALIZATION
# ---------------------------------------------------------------------------

try:
    _policy = ConfigManager()
    _USE_POLICY = True
    print(f"[Router] PolicyManager loaded from {_policy.path}")
except Exception as e:
    _USE_POLICY = False
    _policy = None
    print(f"[Router] PolicyManager failed to load: {e}")

_PROVIDER_CACHE = load_cache()

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
# ZERO-BUDGET DETECTION
# ---------------------------------------------------------------------------

def _has_any_paid_key() -> bool:
    """Tarkistaa, onko yhtään maksullista API-avainta asetettu."""
    return any([
        get_env_value("MICROSOFT_TRANSLATOR_KEY"),
        get_env_value("DEEPL_API_KEY"),
        get_env_value("GOOGLE_API_KEY"),
        get_env_value("NAVER_CLIENT_ID"),
    ])


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
    mymemory_email: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]:
    """
    Palauttaa providerit käyttöjärjestyksessä.
    """

    # --- Policy-manager mode ---
    if _USE_POLICY and _policy is not None:
        available = _policy.get_available_providers()
        if available:
            # Normalisoi pieniksi kirjaimiksi
            return [name.lower() for name in available]

    # --- Nolla-budjetti: fast path ---
    if not _has_any_paid_key():
        mymemory_email = mymemory_email or get_env_value("MYMEMORY_EMAIL")
        if mymemory_email:
            return ["mymemory"]
        return ["libretranslate"]

    # --- Legacy cache-based mode ---
    providers_cache = _PROVIDER_CACHE.get("providers", {})

    pg_langs = {code.lower() for code in providers_cache.get("papago", [])}
    mm_langs = {code.lower() for code in providers_cache.get("mymemory_iso_639_1", [])}
    ms_langs = {code.lower() for code in providers_cache.get("microsoft_translator", {})}
    lt_langs = {code.lower() for code in providers_cache.get("libretranslate", {})}

    providers: List[str] = []

    ms_key = microsoft_api_key or get_env_value("MICROSOFT_TRANSLATOR_KEY")
    if ms_key and _ms_registry.is_available():
        if source_lang.lower() in ms_langs and target_lang.lower() in ms_langs:
            providers.append("microsoft_translator")

    deepl_key = deepl_key or get_env_value("DEEPL_API_KEY")
    if deepl_key:
        providers.append("deepl")

    google_api_key = google_api_key or get_env_value("GOOGLE_API_KEY")
    if google_api_key:
        if _google_registry.is_pair_supported(source_lang, target_lang):
            providers.append("google")

    papago_client_id = papago_client_id or get_env_value("NAVER_CLIENT_ID")
    papago_client_secret = papago_client_secret or get_env_value("NAVER_CLIENT_SECRET")
    static_pg = (
        source_lang.lower() in pg_langs and
        target_lang.lower() in pg_langs
    )
    if papago_client_id and papago_client_secret:
        if _papago_registry.is_pair_supported(source_lang, target_lang, static_pg):
            providers.append("papago")

    if source_lang.lower() in lt_langs and target_lang.lower() in lt_langs:
        if _libre_registry.is_pair_supported(source_lang, target_lang):
            providers.append("libretranslate")

    mymemory_email = mymemory_email or get_env_value("MYMEMORY_EMAIL")
    if mymemory_email:
        providers.append("mymemory")
    elif source_lang.lower() in mm_langs and target_lang.lower() in mm_langs:
        providers.append("mymemory")

    if not providers:
        providers.append("mymemory")

    return providers


def get_provider_timeout(provider_name: str) -> float:
    """Hakee providerin timeoutin policy-managerista tai oletuksen."""
    if _USE_POLICY and _policy is not None:
        return _policy.get_timeout(provider_name, default=10.0)
    return 10.0


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
    mymemory_email: Optional[str] = None,
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
        mymemory_email,
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
        mymemory_email,
        request,
    )

    print(f"[Router] Provider order: {order}")  # DEBUG

    ms_key = microsoft_api_key or get_env_value("MICROSOFT_TRANSLATOR_KEY")

    for service in order:
        if time.time() - start_time > total_timeout:
            break

        provider_timeout = get_provider_timeout(service)
        service_deadline = min(
            start_time + total_timeout,
            time.time() + provider_timeout
        )

        for attempt in range(max_retries):
            if time.time() > service_deadline:
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
                if time.time() + backoff > service_deadline:
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
    except ServiceUnavailableError as e:
        logger.warning(
            "Translation failed for '%s...' (%s -> %s): %s",
            text[:50], source_lang, target_lang, e,
        )
        return text
    except Exception as e:
        logger.error(
            "Unexpected translation error for '%s...': %s",
            text[:50], e,
            exc_info=True,
        )
        return text

