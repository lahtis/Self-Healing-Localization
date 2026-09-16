from shl.engine.language_detection.providers.detect_language import (
    DetectLanguageAdapter,
)
from shl.engine.translation.exceptions import InvalidRequestError


def test_detect_language_multiple_languages():
    adapter = DetectLanguageAdapter()

    tests = [
        ("fi", "Tämä on testi suomen kielen tunnistamiselle."),
        ("en", "This is a test for English language detection."),
        ("fr", "Bonjour, comment allez-vous aujourd'hui ?"),
        ("de", "Guten Morgen, wie geht es Ihnen heute?"),
        ("es", "Hola, ¿cómo estás hoy?"),
        ("it", "Buongiorno, come stai oggi?"),
        ("sv", "Hej, hur mår du idag?"),
        ("pt", "Olá, como você está hoje?"),
        ("nl", "Hallo, hoe gaat het vandaag met je?"),
        ("pl", "Dzień dobry, jak się dzisiaj masz?"),
        ("ja", "こんにちは。今日は元気ですか？"),
        ("zh", "你好，今天过得怎么样？"),
        ("ko", "안녕하세요. 오늘 어떻게 지내세요?"),
        ("ru", "Здравствуйте, как вы сегодня?"),
    ]

    for expected_language, text in tests:
        results = adapter.detect(text)

        assert results
        assert results[0].language == expected_language
        assert results[0].provider == adapter.name
        assert results[0].score is not None


def test_detect_language_empty_text():
    adapter = DetectLanguageAdapter()

    try:
        adapter.detect("")
    except InvalidRequestError:
        pass
    else:
        raise AssertionError("Empty text was accepted.")


def test_detect_language_whitespace_text():
    adapter = DetectLanguageAdapter()

    try:
        adapter.detect("   ")
    except InvalidRequestError:
        pass
    else:
        raise AssertionError("Whitespace-only text was accepted.")


def test_detect_language_none():
    adapter = DetectLanguageAdapter()

    try:
        adapter.detect(None)
    except InvalidRequestError:
        pass
    else:
        raise AssertionError("None was accepted.")
