"""
Tests for SHL TranslationProcessor.
"""

import pytest

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation.placeholder import (
    PlaceholderIntegrityError,
)
from shl.engine.translation.processor import (
    TranslationProcessor,
)


def make_request(
    text: str,
    *,
    html_format: bool = False,
) -> TranslationRequest:
    """Create a basic translation request."""
    return TranslationRequest(
        text=text,
        source_lang="en",
        target_lang="fi",
        html_format=html_format,
    )


def test_plain_translation() -> None:
    """Plain text should be passed to the translator."""
    calls: list[str] = []

    def translator(request: TranslationRequest) -> str:
        calls.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = make_request("Hello world")

    result = processor.process(request)

    assert result.text == "HELLO WORLD"
    assert result.had_html is False
    assert result.placeholder_count == 0
    assert calls == ["Hello world"]


def test_empty_text() -> None:
    """Empty text should not invoke the translator."""
    called = False

    def translator(request: TranslationRequest) -> str:
        nonlocal called
        called = True
        return request.text

    processor = TranslationProcessor(
        translator
    )

    request = make_request("")

    result = processor.process(request)

    assert result.text == ""
    assert result.had_html is False
    assert result.placeholder_count == 0
    assert called is False


def test_placeholder_is_protected_and_restored() -> None:
    """Placeholders must survive translation unchanged."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{[^{}]+\}",
    )

    request = make_request(
        "Hello {name}"
    )

    result = processor.process(request)

    assert result.text == "HELLO {name}"
    assert result.placeholder_count == 1
    assert received[0] != "Hello {name}"
    assert "{name}" not in received[0]


def test_multiple_placeholders() -> None:
    """Multiple placeholders must all be preserved."""
    def translator(request: TranslationRequest) -> str:
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{[^{}]+\}",
    )

    request = make_request(
        "Hello {first_name} {last_name}"
    )

    result = processor.process(request)

    assert result.text == (
        "HELLO {first_name} {last_name}"
    )
    assert result.placeholder_count == 2


def test_html_is_detected() -> None:
    """HTML-like markup should be detected."""
    def translator(request: TranslationRequest) -> str:
        return request.text

    processor = TranslationProcessor(
        translator
    )

    request = make_request(
        "<p>Hello world</p>"
    )

    result = processor.process(request)

    assert result.had_html is True


def test_html_is_preserved_when_processing_is_disabled() -> None:
    """HTML should remain untouched when HTML processing is disabled."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = make_request(
        "<p>Hello world</p>",
        html_format=False,
    )

    result = processor.process(request)

    assert result.text == "<P>HELLO WORLD</P>"
    assert received == ["<p>Hello world</p>"]


def test_html_text_is_processed_when_enabled() -> None:
    """Only textual HTML content should be translated."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = make_request(
        "<p>Hello <strong>world</strong>!</p>",
        html_format=True,
    )

    result = processor.process(request)

    assert result.text == (
        "<p>HELLO <strong>WORLD</strong>!</p>"
    )

    assert received == [
        "Hello ",
        "world",
        "!",
    ]


def test_html_attributes_are_preserved() -> None:
    """HTML attributes must not be translated or modified."""
    def translator(request: TranslationRequest) -> str:
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = make_request(
        '<a href="/save" class="button">Save</a>',
        html_format=True,
    )

    result = processor.process(request)

    assert result.text == (
        '<a href="/save" class="button">SAVE</a>'
    )


def test_html_entities_are_preserved() -> None:
    """HTML entities must remain unchanged."""
    def translator(request: TranslationRequest) -> str:
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = make_request(
        "<p>Hello&nbsp;world</p>",
        html_format=True,
    )

    result = processor.process(request)

    assert result.text == (
        "<p>HELLO&nbsp;WORLD</p>"
    )


def test_html_placeholder_is_preserved() -> None:
    """Placeholders inside HTML text must survive translation."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{\{[^{}]+\}\}",
    )

    request = make_request(
        "<p>Hello {{name}}</p>",
        html_format=True,
    )

    result = processor.process(request)

    assert result.text == (
        "<p>HELLO {{name}}</p>"
    )

    assert result.placeholder_count == 1
    assert "{{name}}" not in received[0]


def test_request_metadata_is_preserved() -> None:
    """Request metadata must survive preprocessing."""
    received: list[TranslationRequest] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request)
        return request.text.upper()

    processor = TranslationProcessor(
        translator
    )

    request = TranslationRequest(
        text="Save",
        source_lang="en",
        target_lang="fi",
        context_type="button",
        domain="desktop_ui",
        formality="formal",
        honorific=False,
        glossary={"Save": "Tallenna"},
        glossary_id="glossary-1",
        html_format=False,
        key="settings.save",
        screen="settings",
        component="save_button",
        source_id="shl://settings/save_button",
        metadata={
            "test": True,
        },
    )

    result = processor.process(request)

    assert result.text == "SAVE"

    assert len(received) == 1

    translated_request = received[0]

    assert translated_request.source_lang == "en"
    assert translated_request.target_lang == "fi"
    assert translated_request.context_type == "button"
    assert translated_request.domain == "desktop_ui"
    assert translated_request.formality == "formal"
    assert translated_request.honorific is False
    assert translated_request.glossary == {
        "Save": "Tallenna"
    }
    assert translated_request.glossary_id == "glossary-1"
    assert translated_request.key == "settings.save"
    assert translated_request.screen == "settings"
    assert translated_request.component == "save_button"
    assert translated_request.source_id == (
        "shl://settings/save_button"
    )
    assert translated_request.metadata == {
        "test": True,
    }


def test_original_request_is_not_modified() -> None:
    """Processing must not mutate the original request."""
    def translator(request: TranslationRequest) -> str:
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{[^{}]+\}",
    )

    request = make_request(
        "Hello {name}"
    )

    original_text = request.text

    processor.process(request)

    assert request.text == original_text


def test_missing_placeholder_is_detected() -> None:
    """Removing a placeholder must raise an integrity error."""
    def translator(request: TranslationRequest) -> str:
        return "HELLO"

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{[^{}]+\}",
    )

    request = make_request(
        "Hello {name}"
    )

    with pytest.raises(PlaceholderIntegrityError):
        processor.process(request)


def test_duplicated_placeholder_is_detected() -> None:
    """Duplicating a placeholder must raise an integrity error."""
    def translator(request: TranslationRequest) -> str:
        token = request.text.split(" ")[-1]
        return f"HELLO {token} {token}"

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{[^{}]+\}",
    )

    request = make_request(
        "Hello {name}"
    )

    with pytest.raises(PlaceholderIntegrityError):
        processor.process(request)


def test_custom_placeholder_matcher() -> None:
    """Custom matcher should work without a hardcoded syntax."""
    def matcher(
        text: str,
    ) -> list[tuple[int, int]]:
        start = text.find("%USERNAME%")

        if start == -1:
            return []

        return [
            (
                start,
                start + len("%USERNAME%"),
            )
        ]

    def translator(request: TranslationRequest) -> str:
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_matcher=matcher,
    )

    request = make_request(
        "Hello %USERNAME%"
    )

    result = processor.process(request)

    assert result.text == (
        "HELLO %USERNAME%"
    )

    assert result.placeholder_count == 1

def test_multiple_html_text_nodes_with_placeholders() -> None:
    """Placeholders in separate HTML text nodes must remain isolated."""
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)
        return request.text.upper()

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{\{[^{}]+\}\}",
    )

    request = make_request(
        "<p>Hello {{name}}</p><p>Welcome {{user}}</p>",
        html_format=True,
    )

    result = processor.process(request)

    assert result.text == (
        "<p>HELLO {{name}}</p>"
        "<p>WELCOME {{user}}</p>"
    )

    assert result.placeholder_count == 2

    assert len(received) == 2

    assert "{{name}}" not in received[0]
    assert "{{user}}" not in received[1]


