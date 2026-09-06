"""
File: test_guestbook_placeholder_integration.py
Description:
    Verify the complete Guestbook placeholder translation flow.

    The Guestbook uses "{}" as a Python str.format() placeholder.
    SHL must protect it during translation and restore it unchanged.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation import router


def test_guestbook_saved_placeholder_flow() -> None:
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)

        # The provider must never receive the active "{}" placeholder.
        assert "{}" not in request.text

        # Simulate provider translation.
        return request.text.replace(
            "Saved:",
            "Сохранено:",
        )

    request = TranslationRequest(
        text="Saved: {}",
        source_lang="en",
        target_lang="ru",
        placeholder_pattern=r"\{\}",
    )

    translated = router._translate_with_processor(
        request,
        translator,
        False,
    )

    assert received[0] != "Saved: {}"
    assert "{}" not in received[0]

    assert translated == "Сохранено: {}"

    # The restored placeholder must remain usable by str.format().
    final_text = translated.format("Hello world")

    assert final_text == "Сохранено: Hello world"


if __name__ == "__main__":
    test_guestbook_saved_placeholder_flow()


