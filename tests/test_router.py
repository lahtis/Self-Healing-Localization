"""
Tests for SHL Router HTML policy handling.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation import router
from shl.engine.translation.exceptions import LanguageNotSupportedError


def test_provider_html_policy_deny() -> None:
    """Provider denying HTML should return False."""
    original_use_policy = router._USE_POLICY

    try:
        router._USE_POLICY = True

        result = router.get_provider_html_policy(
            "mymemory"
        )

        assert result is False

    finally:
        router._USE_POLICY = original_use_policy


def test_provider_html_policy_allow() -> None:
    """Provider explicitly allowing HTML should return True."""
    original_use_policy = router._USE_POLICY

    try:
        router._USE_POLICY = True

        result = router.get_provider_html_policy(
            "google"
        )

        assert result is True

    finally:
        router._USE_POLICY = original_use_policy


def test_provider_html_policy_case_insensitive() -> None:
    """Provider names should be matched case-insensitively."""
    original_use_policy = router._USE_POLICY

    try:
        router._USE_POLICY = True

        result = router.get_provider_html_policy(
            "Google"
        )

        assert result is True

    finally:
        router._USE_POLICY = original_use_policy


def test_provider_html_policy_unknown_provider() -> None:
    """Unknown providers should have no explicit HTML policy."""
    original_use_policy = router._USE_POLICY

    try:
        router._USE_POLICY = True

        result = router.get_provider_html_policy(
            "unknown_provider"
        )

        assert result is None

    finally:
        router._USE_POLICY = original_use_policy


def test_provider_html_policy_disabled() -> None:
    """Disabled PolicyManager should return no explicit policy."""
    original_use_policy = router._USE_POLICY

    try:
        router._USE_POLICY = False

        result = router.get_provider_html_policy(
            "mymemory"
        )

        assert result is None

    finally:
        router._USE_POLICY = original_use_policy


def test_blacklisted_deepl_pair_skips_adapter() -> None:
    """A rejected DeepL pair must not construct an adapter again."""
    original_priority = router.get_provider_priority
    original_adapter = router.DeepLAdapter

    class UnexpectedAdapter:
        def __init__(self, *args, **kwargs):
            raise AssertionError("blacklisted DeepL pair reached adapter")

    router._deepl_registry.clear_blacklist()
    router._deepl_registry.mark_pair_unsupported("en", "zh-cn")
    router.get_provider_priority = lambda **kwargs: ["deepl"]
    router.DeepLAdapter = UnexpectedAdapter

    try:
        try:
            router.translate_text_with_metadata(
                "Guestbook",
                target_lang="zh-cn",
                source_lang="en",
                max_retries=1,
            )
        except LanguageNotSupportedError:
            pass
        else:
            raise AssertionError("expected no available translation service")
    finally:
        router.get_provider_priority = original_priority
        router.DeepLAdapter = original_adapter
        router._deepl_registry.clear_blacklist()

def test_translate_with_processor_denies_html() -> None:
    """HTML-denying providers must receive text without HTML markup."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    request = TranslationRequest(
        text="<p>Hello</p>",
        source_lang="en",
        target_lang="fi",
        html_format=True,
    )

    result = router._translate_with_processor(
        request,
        translator,
        False,
    )

    assert result == "<p>HELLO</p>"
    assert received == ["Hello"]


def test_translate_with_processor_allows_html() -> None:
    """HTML-accepting providers must receive the original HTML."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    request = TranslationRequest(
        text="<p>Hello</p>",
        source_lang="en",
        target_lang="fi",
        html_format=True,
    )

    result = router._translate_with_processor(
        request,
        translator,
        True,
    )

    assert result == "<P>HELLO</P>"
    assert received == ["<p>Hello</p>"]


def test_translate_with_processor_undefined_policy_preserves_behavior() -> None:
    """Undefined HTML policy must follow request.html_format."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    request = TranslationRequest(
        text="<p>Hello</p>",
        source_lang="en",
        target_lang="fi",
        html_format=False,
    )

    result = router._translate_with_processor(
        request,
        translator,
        None,
    )

    assert result == "<P>HELLO</P>"
    assert received == ["<p>Hello</p>"]


def test_translate_with_processor_undefined_policy_with_html_format() -> None:
    """Undefined policy must process HTML when html_format is enabled."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    request = TranslationRequest(
        text="<p>Hello</p>",
        source_lang="en",
        target_lang="fi",
        html_format=True,
    )

    result = router._translate_with_processor(
        request,
        translator,
        None,
    )

    assert result == "<p>HELLO</p>"
    assert received == ["Hello"]

def test_translate_with_processor_placeholder_is_not_configured() -> None:
    received: list[str] = []

    def translator(request) -> str:
        received.append(request.text)
        return "Сохранено:"

    request = TranslationRequest(
        text="Saved: {}",
        source_lang="en",
        target_lang="ru",
    )

    result = router._translate_with_processor(
        request,
        translator,
        False,
    )

    assert result == "Сохранено:"
    assert received == ["Saved: {}"]
