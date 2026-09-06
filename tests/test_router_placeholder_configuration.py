"""
File: test_router_placeholder_configuration.py
Description:
    Verify that a placeholder pattern can be passed through the
    Router translation pipeline and preserved during translation.

    This test is expected to fail with the current Router because
    placeholder_pattern is not yet part of the Router API.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation import router


def test_router_accepts_placeholder_pattern() -> None:
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)

        # Simulate a translation provider.
        return request.text.replace("Saved:", "Сохранено:")

    request = TranslationRequest(
        text="Saved: {}",
        source_lang="en",
        target_lang="ru",
    )

    result = router._translate_with_processor(
        request,
        translator,
        False,
        placeholder_pattern=r"\{\}",
    )

    print("Input:       ", request.text)
    print("Sent to API: ", received[0])
    print("Result:      ", result)

    assert "{}" not in received[0]
    assert result == "Сохранено: {}"


if __name__ == "__main__":
    test_router_accepts_placeholder_pattern()


