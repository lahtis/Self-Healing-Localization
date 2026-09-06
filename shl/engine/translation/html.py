"""
File: shl/engine/translation/html.py
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.10
Description:
    HTML-aware translation helpers for SHL.

    Provides:
        - lightweight HTML detection
        - preservation of original HTML markup
        - translation of textual HTML content
        - HTML structure validation
        - provider-independent placeholder protection hooks

    This module does not select translation providers.
    Provider selection and policy handling belong to the Router.
"""

import re
from html.parser import HTMLParser
from typing import Callable, Optional


class HTMLIntegrityError(ValueError):
    """Raised when the HTML structure changes during translation."""


class HTMLDetector:
    """
    Lightweight detector for likely HTML markup.

    The detector intentionally does not treat every '<' or '>' character
    as HTML. It looks for an opening or closing tag-like construct.

    This class only detects HTML. It does not decide how HTML should be
    processed.
    """

    _TAG_RE = re.compile(
        r"<\s*/?\s*[A-Za-z][^>]*>"
    )

    @classmethod
    def contains_html(cls, text: str) -> bool:
        """
        Return True when text appears to contain HTML markup.
        """
        if not isinstance(text, str) or not text:
            return False

        return bool(cls._TAG_RE.search(text))


class HTMLStructureParser(HTMLParser):
    """
    Extract HTML structure without reconstructing the HTML.

    Text nodes are intentionally ignored.

    The parser records:
        - start tags
        - end tags
        - self-closing tags
        - comments
        - declarations
        - processing instructions
        - unknown declarations

    Attribute values are included in the structure so that changes to
    HTML attributes are detected as well.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.structure: list[tuple] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, Optional[str]]],
    ) -> None:
        self.structure.append(
            (
                "start",
                tag.lower(),
                tuple(
                    (
                        name.lower(),
                        value,
                    )
                    for name, value in attrs
                ),
            )
        )

    def handle_endtag(self, tag: str) -> None:
        self.structure.append(
            ("end", tag.lower())
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, Optional[str]]],
    ) -> None:
        self.structure.append(
            (
                "startend",
                tag.lower(),
                tuple(
                    (
                        name.lower(),
                        value,
                    )
                    for name, value in attrs
                ),
            )
        )

    def handle_comment(self, data: str) -> None:
        self.structure.append(
            ("comment", data)
        )

    def handle_decl(self, decl: str) -> None:
        self.structure.append(
            ("decl", decl)
        )

    def handle_pi(self, data: str) -> None:
        self.structure.append(
            ("pi", data)
        )

    def unknown_decl(self, data: str) -> None:
        self.structure.append(
            ("unknown_decl", data)
        )


class HTMLTextProcessor:
    """
    Process textual content inside HTML while preserving original markup.

    The supplied text processor is called only for normal text nodes.

    HTML tags, attributes, comments, declarations, entities and character
    references are preserved without sending them to the text processor.

    Example:

        <p>Hello <b>world</b>!</p>

    The text processor receives:

        "Hello "
        "world"
        "!"

    The original HTML representation is retained.
    """

    def __init__(
        self,
        text_processor: Callable[[str], str],
    ) -> None:
        if not callable(text_processor):
            raise TypeError(
                "text_processor must be callable."
            )

        self._processor = text_processor

    def process(self, html: str) -> str:
        """
        Process HTML text nodes and return the reconstructed result.

        The HTML markup itself is not reconstructed from parsed attributes.
        Original start-tag text is retained where possible.
        """
        if not isinstance(html, str):
            raise TypeError("html must be a string.")

        parser = _HTMLReplacementParser(
            self._processor
        )

        parser.feed(html)
        parser.close()

        return parser.result()


class _HTMLReplacementParser(HTMLParser):
    """
    Internal parser used by HTMLTextProcessor.

    The parser deliberately preserves the original source representation
    of markup instead of serializing it back into HTML.
    """

    def __init__(
        self,
        text_processor: Callable[[str], str],
    ) -> None:
        super().__init__(convert_charrefs=False)

        self._processor = text_processor
        self._parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, Optional[str]]],
    ) -> None:
        original = self.get_starttag_text()

        if original is not None:
            self._parts.append(original)
        else:
            self._parts.append(
                f"<{tag}>"
            )

    def handle_endtag(self, tag: str) -> None:
        self._parts.append(
            f"</{tag}>"
        )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, Optional[str]]],
    ) -> None:
        original = self.get_starttag_text()

        if original is not None:
            self._parts.append(original)
        else:
            self._parts.append(
                f"<{tag} />"
            )

    def handle_data(self, data: str) -> None:
        """
        Send only normal textual content to the supplied processor.
        """
        self._parts.append(
            self._processor(data)
        )

    def handle_entityref(self, name: str) -> None:
        """
        Preserve named HTML entities exactly.
        """
        self._parts.append(
            f"&{name};"
        )

    def handle_charref(self, name: str) -> None:
        """
        Preserve numeric HTML character references exactly.
        """
        self._parts.append(
            f"&#{name};"
        )

    def handle_comment(self, data: str) -> None:
        self._parts.append(
            f"<!--{data}-->"
        )

    def handle_decl(self, decl: str) -> None:
        self._parts.append(
            f"<!{decl}>"
        )

    def handle_pi(self, data: str) -> None:
        self._parts.append(
            f"<?{data}>"
        )

    def unknown_decl(self, data: str) -> None:
        self._parts.append(
            f"<![{data}]>"
        )

    def result(self) -> str:
        """
        Return the processed HTML.
        """
        return "".join(self._parts)


class TranslationIntegrityValidator:
    """
    Validate translation-related structural integrity.

    HTML validation compares the parsed structure of the original and
    translated HTML. Text content is deliberately ignored.
    """

    @staticmethod
    def validate_html(
        original: str,
        translated: str,
    ) -> None:
        """
        Raise HTMLIntegrityError if the HTML structure changed.
        """
        if not isinstance(original, str):
            raise TypeError("original must be a string.")

        if not isinstance(translated, str):
            raise TypeError("translated must be a string.")

        original_parser = HTMLStructureParser()
        translated_parser = HTMLStructureParser()

        try:
            original_parser.feed(original)
            original_parser.close()

            translated_parser.feed(translated)
            translated_parser.close()
        except Exception as exc:
            raise HTMLIntegrityError(
                f"Unable to validate HTML structure: {exc}"
            ) from exc

        if (
            original_parser.structure
            != translated_parser.structure
        ):
            raise HTMLIntegrityError(
                "HTML structure changed during translation."
            )


def translate_html_text(
    html: str,
    translator: Callable[[str], str],
) -> str:
    """
    Translate textual content inside HTML.

    The translator receives individual textual HTML nodes.

    This function does not select a provider and does not perform
    placeholder detection. Those responsibilities belong to the
    translation pipeline and Router.
    """
    if not callable(translator):
        raise TypeError(
            "translator must be callable."
        )

    processor = HTMLTextProcessor(
        translator
    )

    result = processor.process(html)

    TranslationIntegrityValidator.validate_html(
        html,
        result,
    )

    return result


__all__ = [
    "HTMLDetector",
    "HTMLIntegrityError",
    "HTMLStructureParser",
    "HTMLTextProcessor",
    "TranslationIntegrityValidator",
    "translate_html_text",
]
