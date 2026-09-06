"""
File: test_translate_text_placeholder_configuration.py
Description:
    Verify that the public translate_text() API accepts and forwards
    per-request placeholder configuration.
"""

from shl.engine.translation import router
from shl.engine.translation.metadata import TranslationResult


def test_translate_text_accepts_placeholder_pattern() -> None:
    received: dict[str, object] = {}

    def fake_translate_text_with_metadata(
        *,
        text: str,
        target_lang: str,
        source_lang: str = "en",
        use_cache: bool = True,
        mymemory_email=None,
        mymemory_api_key=None,
        deepl_key=None,
        google_api_key=None,
        google_backup_api_key=None,
        papago_client_id=None,
        papago_client_secret=None,
        microsoft_api_key=None,
        yandex_api_key=None,
        local_api_key=None,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        total_timeout: float = 30.0,
        placeholder_pattern=None,
        request=None,
    ) -> TranslationResult:
        received["text"] = text
        received["placeholder_pattern"] = placeholder_pattern

        return TranslationResult(
            translated_text="Сохранено: {}",
            source="test",
        )

    original = router.translate_text_with_metadata

    try:
        router.translate_text_with_metadata = (
            fake_translate_text_with_metadata
        )

        result = router.translate_text(
            text="Saved: {}",
            target_lang="ru",
            source_lang="en",
            placeholder_pattern=r"\{\}",
        )

    finally:
        router.translate_text_with_metadata = original

    assert received["text"] == "Saved: {}"
    assert received["placeholder_pattern"] == r"\{\}"
    assert result == "Сохранено: {}"


if __name__ == "__main__":
    test_translate_text_accepts_placeholder_pattern()


