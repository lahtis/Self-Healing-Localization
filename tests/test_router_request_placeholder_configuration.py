"""
File: test_router_request_placeholder_configuration.py
Description:
    Verify that Router preserves per-request placeholder configuration
    when passing a TranslationRequest through TranslationProcessor.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation import router


def test_router_preserves_request_placeholder_pattern() -> None:
    received: list[str] = []

    def translator(request: TranslationRequest) -> str:
        received.append(request.text)

        # The Router must pass the request configuration to the processor.
        assert request.placeholder_pattern == r"\{\}"

        # Simulate a translation provider.
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

    result = router._translate_with_processor(
        request,
        translator,
        False,
    )

    print("Input:       ", request.text)
    print("Sent to API: ", received[0])
    print("Result:      ", result)

    assert "{}" not in received[0]
    assert result == "Сохранено: {}"


if __name__ == "__main__":
    test_router_preserves_request_placeholder_pattern()


