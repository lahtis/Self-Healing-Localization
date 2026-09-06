
"""
File: test_guestbook_placeholder.py
Description:
    Verify that the Guestbook-style "{}" placeholder survives
    the SHL TranslationProcessor pipeline.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation.processor import TranslationProcessor


def test_guestbook_placeholder_survives_translation() -> None:
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)

        # Simulate translation while preserving the protected token.
        return request.text.replace("Saved:", "Сохранено:")

    processor = TranslationProcessor(
        translator,
        placeholder_pattern=r"\{\}",
    )

    request = TranslationRequest(
        text="Saved: {}",
        source_lang="en",
        target_lang="ru",
    )

    result = processor.process(request)

    print("Input:       ", request.text)
    print("Sent to API: ", received[0])
    print("Result:      ", result.text)

    # The placeholder must be protected before translation.
    assert received[0].startswith("Saved: ")
    assert "{}" not in received[0]

    # The original placeholder must be restored after translation.
    assert result.text == "Сохранено: {}"
    assert "{}" in result.text

    print("PASS: placeholder survived translation.")


if __name__ == "__main__":
    test_guestbook_placeholder_survives_translation()


