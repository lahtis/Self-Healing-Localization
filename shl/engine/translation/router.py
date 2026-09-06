"""
File: router.py — Policy-aware routing for SHL translation ecosystem.
Author: Tuomas Lähteenmäki
Version: 0.2.11
License: MIT
"""

import time
import logging
from typing import Optional, List, Dict, Any, Callable

from .provider_cache import load_cache
from .cache import TranslationCache
from .metadata import TranslationRequest, TranslationResult
from .exceptions import (
    TranslationError,
    ServiceUnavailableError,
    LanguageNotSupportedError,
    RateLimitExceededError,
)
from .processor import TranslationProcessor

from .providers.mymemory import MyMemoryAdapter
from .providers.mymemory_registry import MyMemoryRegistry

from .providers.microsoft import MicrosoftTranslatorAdapter
from .providers.microsoft_registry import MicrosoftServiceRegistry

from .providers.libretranslate import LibreTranslateAdapter
from .providers.libretranslate_registry import LibreTranslateRegistry
from .providers.libretranslate_mirrors import LibreTranslateMirrorManager

from .providers.deepl import DeepLAdapter
from .providers.deepl_registry import DeepLRegistry

from .providers.googlev2 import GoogleV2Adapter
from .providers.google_registry import GoogleRegistry

from .providers.papago import PapagoAdapter
from .providers.papago_registry import PapagoRegistry

from .providers.yandex import YandexAdapter
from .providers.yandex_registry import YandexRegistry

from .providers.local_translator import LocalTranslatorAdapter
from .providers.local_translator_registry import LocalRegistry

from shl.config import get_config_value
from shl.config.policy_manager import ConfigManager
from shl.utils.env_loader import get_env_value


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
_yandex_registry = YandexRegistry()
_local_registry = LocalRegistry()

_ms_registry = MicrosoftServiceRegistry(
    ttl_seconds=get_config_value("microsoft_translator.ttl")
)


# ---------------------------------------------------------------------------
# HTML POLICY
# ---------------------------------------------------------------------------

_POLICY_PROVIDER_NAMES = {
    "mymemory": "MyMemory",
    "libretranslate": "LibreTranslate",
    "deepl": "DeepL",
    "google": "Google",
    "microsoft_translator": "MicrosoftTranslator",
    "papago": "Papago",
    "yandex": "Yandex",
    "local": "Local",
}


def get_provider_html_policy(
    provider_name: str,
) -> Optional[bool]:
    """
    Return the HTML handling policy for a provider.

    Returns:
        True:
            Provider explicitly allows HTML.

        False:
            Provider explicitly denies HTML, so SHL must preprocess it.

        None:
            Policy does not explicitly define HTML handling.
    """
    if not _USE_POLICY or _policy is None:
        return None

    policy_name = _POLICY_PROVIDER_NAMES.get(
        provider_name.lower()
    )

    if policy_name is None:
        return None

    provider = _policy.get_provider(
        policy_name
    )

    if not provider:
        return None

    allow = provider.get(
        "allow",
        [],
    )

    deny = provider.get(
        "deny",
        [],
    )

    if not isinstance(allow, list):
        allow = []

    if not isinstance(deny, list):
        deny = []

    normalized_allow = {
        str(value).lower()
        for value in allow
    }

    normalized_deny = {
        str(value).lower()
        for value in deny
    }

    # Explicit deny takes precedence.
    if "html" in normalized_deny:
        return False

    if "html" in normalized_allow:
        return True

    return None

def _translate_with_processor(
    request: TranslationRequest,
    translator: Callable[[TranslationRequest], str],
    html_policy: Optional[bool],
) -> str:
    """
    Translate a request through TranslationProcessor when required.

    HTML policy semantics:

        False:
            Provider denies HTML. SHL preprocesses HTML.

        True:
            Provider explicitly accepts HTML. Original request is sent
            directly to the provider.

        None:
            Preserve the request's existing html_format behavior.

    Placeholder configuration is carried by TranslationRequest and
    passed to TranslationProcessor unchanged.
    """
    if html_policy is True:
        return translator(request)

    if html_policy is False:
        if request.html_format:
            return TranslationProcessor(
                translator,
                placeholder_pattern=request.placeholder_pattern,
            ).process(request).text

        forced_request = TranslationRequest(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            context_type=request.context_type,
            domain=request.domain,
            formality=request.formality,
            honorific=request.honorific,
            glossary=request.glossary,
            glossary_id=request.glossary_id,
            html_format=True,
            placeholder_pattern=request.placeholder_pattern,
            key=request.key,
            screen=request.screen,
            component=request.component,
            source_id=request.source_id,
            metadata=request.metadata,
        )

        return TranslationProcessor(
            translator,
            placeholder_pattern=forced_request.placeholder_pattern,
        ).process(forced_request).text

    if request.html_format:
        return TranslationProcessor(
            translator,
            placeholder_pattern=request.placeholder_pattern,
        ).process(request).text

    return translator(request)


# ---------------------------------------------------------------------------
# ZERO-BUDGET DETECTION
# ---------------------------------------------------------------------------

def _has_any_paid_key() -> bool:
    """Check whether any paid translation provider API key is configured."""
    return any([
        get_env_value("MICROSOFT_TRANSLATOR_KEY"),
        get_env_value("DEEPL_API_KEY"),
        get_env_value("GOOGLE_API_KEY"),
        get_env_value("NAVER_CLIENT_ID"),
        get_env_value("YANDEX_API_KEY"),
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
    yandex_api_key: Optional[str] = None,
    local_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> List[str]:
    """
    Return translation providers in priority order.
    """

    # --- Policy-manager mode ---
    if _USE_POLICY and _policy is not None:
        available = _policy.get_available_providers()
        if available:
            return [name.lower() for name in available]

    # --- Zero-budget fast path ---
    if not _has_any_paid_key():
        mymemory_email = mymemory_email or get_env_value("MYMEMORY_EMAIL")

        if mymemory_email:
            return ["mymemory"]

        return ["libretranslate"]

    # --- Legacy cache-based mode ---
    providers_cache = _PROVIDER_CACHE.get("providers", {})

    pg_langs = {
        code.lower()
        for code in providers_cache.get("papago", [])
    }

    mm_langs = {
        code.lower()
        for code in providers_cache.get(
            "mymemory_iso_639_1",
            [],
        )
    }

    ms_langs = {
        code.lower()
        for code in providers_cache.get(
            "microsoft_translator",
            {},
        )
    }

    lt_langs = {
        code.lower()
        for code in providers_cache.get(
            "libretranslate",
            {},
        )
    }

    providers: List[str] = []

    ms_key = (
        microsoft_api_key
        or get_env_value("MICROSOFT_TRANSLATOR_KEY")
    )

    if ms_key and _ms_registry.is_available():
        if (
            source_lang.lower() in ms_langs
            and target_lang.lower() in ms_langs
        ):
            providers.append("microsoft_translator")

    deepl_key = deepl_key or get_env_value("DEEPL_API_KEY")

    if deepl_key:
        providers.append("deepl")

    google_api_key = (
        google_api_key
        or get_env_value("GOOGLE_API_KEY")
    )

    if google_api_key:
        if _google_registry.is_pair_supported(
            source_lang,
            target_lang,
        ):
            providers.append("google")

    papago_client_id = (
        papago_client_id
        or get_env_value("NAVER_CLIENT_ID")
    )

    papago_client_secret = (
        papago_client_secret
        or get_env_value("NAVER_CLIENT_SECRET")
    )

    static_pg = (
        source_lang.lower() in pg_langs
        and target_lang.lower() in pg_langs
    )

    if papago_client_id and papago_client_secret:
        if _papago_registry.is_pair_supported(
            source_lang,
            target_lang,
            static_pg,
        ):
            providers.append("papago")

    yandex_api_key = (
        yandex_api_key
        or get_env_value("YANDEX_API_KEY")
    )

    if yandex_api_key:
        if _yandex_registry.is_pair_supported(
            source_lang,
            target_lang,
        ):
            providers.append("yandex")

    if (
        source_lang.lower() in lt_langs
        and target_lang.lower() in lt_langs
    ):
        if _libre_registry.is_pair_supported(
            source_lang,
            target_lang,
        ):
            providers.append("libretranslate")

    mymemory_email = (
        mymemory_email
        or get_env_value("MYMEMORY_EMAIL")
    )

    if mymemory_email:
        providers.append("mymemory")
    elif (
        source_lang.lower() in mm_langs
        and target_lang.lower() in mm_langs
    ):
        providers.append("mymemory")

    if local_api_key or get_env_value("LOCAL_TRANSLATOR_API_KEY"):
        providers.append("local")

    if not providers:
        providers.append("mymemory")

    return providers


def get_provider_timeout(provider_name: str) -> float:
    """Get provider timeout from policy manager or default."""
    if _USE_POLICY and _policy is not None:
        return _policy.get_timeout(
            provider_name,
            default=10.0,
        )

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
    yandex_api_key: Optional[str] = None,
    local_api_key: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str:
    """Return the highest-priority provider."""

    providers = get_provider_priority(
        target_lang=target_lang,
        source_lang=source_lang,
        deepl_key=deepl_key,
        google_api_key=google_api_key,
        papago_client_id=papago_client_id,
        papago_client_secret=papago_client_secret,
        microsoft_api_key=microsoft_api_key,
        mymemory_email=mymemory_email,
        yandex_api_key=yandex_api_key,
        local_api_key=local_api_key,
        request=request,
    )

    return providers[0] if providers else "mymemory"


def get_libretranslate_mirror_stats() -> Dict[str, Any]:
    """Get statistics about LibreTranslate mirrors."""
    return _mirror_manager.get_stats()


# ---------------------------------------------------------------------------
# CLEAR UNAVAILABLE CACHE
# ---------------------------------------------------------------------------

def clear_unavailable_cache() -> None:
    """Clear internal provider and language-pair availability caches."""

    _mirror_manager.clear_blacklist()
    _libre_registry.clear_blacklist()
    _google_registry.clear_blacklist()
    _papago_registry.clear_blacklist()
    _yandex_registry.clear_blacklist()

    _local_registry.clear("local")

    _ms_registry.clear()


# ---------------------------------------------------------------------------
# UNAVAILABLE CACHE STATS
# ---------------------------------------------------------------------------

def get_unavailable_cache_stats() -> Dict[str, Any]:
    """Return statistics for provider availability caches."""

    local_status = _local_registry._status.get("local", {})

    return {
        "blacklisted_mirrors": len(
            _mirror_manager.blacklist
        ),
        "blacklisted_google_pairs": len(
            _google_registry._unsupported_pairs_cache
        ),
        "blacklisted_libre_pairs": len(
            _libre_registry._unsupported_pairs_cache
        ),
        "blacklisted_papago_pairs": len(
            _papago_registry._unsupported_pairs_cache
        ),
        "blacklisted_yandex_pairs": len(
            _yandex_registry._unsupported_pairs_cache
        ),
        "local_tracked_pairs": len(local_status),
        "local_blacklisted_pairs": sum(
            1
            for status in local_status.values()
            if not status.supported
        ),
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
    mymemory_api_key: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    yandex_api_key: Optional[str] = None,
    local_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    placeholder_pattern: Optional[str] = None,
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
            placeholder_pattern=placeholder_pattern,
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
            return TranslationResult(
                translated_text=cached,
                source="cache",
                request_metadata=request,
            )

    order = get_provider_priority(
        target_lang=target_lang,
        source_lang=source_lang,
        deepl_key=deepl_key,
        google_api_key=google_api_key,
        papago_client_id=papago_client_id,
        papago_client_secret=papago_client_secret,
        microsoft_api_key=microsoft_api_key,
        mymemory_email=mymemory_email,
        yandex_api_key=yandex_api_key,
        local_api_key=local_api_key,
        request=request,
    )

    logger.debug(
        "Router provider order: %s",
        order,
    )

    ms_key = (
        microsoft_api_key
        or get_env_value("MICROSOFT_TRANSLATOR_KEY")
    )

    for service in order:
        if time.time() - start_time > total_timeout:
            break

        provider_timeout = get_provider_timeout(service)

        service_deadline = min(
            start_time + total_timeout,
            time.time() + provider_timeout,
        )

        for attempt in range(max_retries):
            if time.time() > service_deadline:
                break

            try:
                translated = None

                if service == "microsoft_translator":
                    adapter = MicrosoftTranslatorAdapter(
                        api_key=ms_key,
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "deepl":
                    adapter = (
                        DeepLAdapter(api_key=deepl_key)
                        if deepl_key
                        else DeepLAdapter()
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "google":
                    adapter = (
                        GoogleV2Adapter(
                            api_key=google_api_key,
                            backup_api_key=google_backup_api_key,
                        )
                        if google_api_key
                        else GoogleV2Adapter()
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "papago":
                    adapter = (
                        PapagoAdapter(
                            client_id=papago_client_id,
                            client_secret=papago_client_secret,
                        )
                        if (
                            papago_client_id
                            and papago_client_secret
                        )
                        else PapagoAdapter()
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "yandex":
                    adapter = (
                        YandexAdapter(
                            api_key=yandex_api_key,
                        )
                        if yandex_api_key
                        else YandexAdapter()
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "libretranslate":
                    adapter = LibreTranslateAdapter(
                        mirror_manager=_mirror_manager,
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "mymemory":
                    adapter = MyMemoryAdapter(
                        email=mymemory_email,
                        api_key=mymemory_api_key,
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                elif service == "local":
                    adapter = LocalTranslatorAdapter(
                        api_key=local_api_key,
                        registry=_local_registry,
                    )
                    translated = _translate_with_processor(
                        request,
                        adapter.translate,
                        get_provider_html_policy(service),
                    )

                if translated is not None:
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

            except LanguageNotSupportedError:
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

                elif service == "papago":
                    _papago_registry.mark_pair_unsupported(
                        source_lang,
                        target_lang,
                    )

                elif service == "yandex":
                    _yandex_registry.mark_pair_unsupported(
                        source_lang,
                        target_lang,
                    )

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
        f"All translation services failed or timed out "
        f"within {total_timeout}s."
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
    mymemory_api_key: Optional[str] = None,
    deepl_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_backup_api_key: Optional[str] = None,
    papago_client_id: Optional[str] = None,
    papago_client_secret: Optional[str] = None,
    microsoft_api_key: Optional[str] = None,
    yandex_api_key: Optional[str] = None,
    local_api_key: Optional[str] = None,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    total_timeout: float = 30.0,
    placeholder_pattern: Optional[str] = None,
    request: Optional[TranslationRequest] = None,
) -> str:

    try:
        result = translate_text_with_metadata(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang,
            use_cache=use_cache,
            mymemory_email=mymemory_email,
            mymemory_api_key=mymemory_api_key,
            deepl_key=deepl_key,
            google_api_key=google_api_key,
            google_backup_api_key=google_backup_api_key,
            papago_client_id=papago_client_id,
            papago_client_secret=papago_client_secret,
            microsoft_api_key=microsoft_api_key,
            yandex_api_key=yandex_api_key,
            local_api_key=local_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            total_timeout=total_timeout,
            placeholder_pattern=placeholder_pattern,
            request=request,
        )

        return result.translated_text

    except ServiceUnavailableError as e:
        logger.warning(
            "Translation failed for '%s...' (%s -> %s): %s",
            text[:50],
            source_lang,
            target_lang,
            e,
        )
        return None

    except Exception as e:
        logger.error(
            "Unexpected translation error for '%s...': %s",
            text[:50],
            e,
            exc_info=True,
        )
        return None

