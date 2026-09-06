"""
File: test_router_guestbook_placeholder.py
Description:
    Verify current Router behavior with a Guestbook-style "{}"
    placeholder when the provider denies HTML handling.
"""

from shl.engine.translation.metadata import TranslationRequest
from shl.engine.translation import router


def test_router_guestbook_placeholder_behavior() -> None:
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
    )

    print("Input:       ", request.text)
    print("Sent to API: ", received[0])
    print("Result:      ", result)

    print()
    print("Placeholder present in input:    ", "{}" in request.text)
    print("Placeholder present at provider: ", "{}" in received[0])
    print("Placeholder present in result:   ", "{}" in result)


if __name__ == "__main__":
    test_router_guestbook_placeholder_behavior()


