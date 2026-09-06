"""
File: test_request_placeholder_configuration.py
Description:
    Verify that placeholder configuration can be carried by
    TranslationRequest and survive the translation pipeline.

    This test defines the intended API for per-request placeholder
    configuration.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation.processor import TranslationProcessor


def test_translation_request_carries_placeholder_pattern() -> None:
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)

        # Verify that placeholder configuration survives request copying.
        assert request.placeholder_pattern == r"\{\}"

        # Simulate a translation provider.
        return request.text.replace("Saved:", "Сохранено:")

    request = TranslationRequest(
        text="Saved: {}",
        source_lang="en",
        target_lang="ru",
        placeholder_pattern=r"\{\}",
    )

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=request.placeholder_pattern,
    )

    result = processor.process(request)

    print("Input:       ", request.text)
    print("Sent to API: ", received[0])
    print("Result:      ", result.text)

    assert request.placeholder_pattern == r"\{\}"
    assert "{}" not in received[0]
    assert result.text == "Сохранено: {}"


if __name__ == "__main__":
    test_translation_request_carries_placeholder_pattern()


