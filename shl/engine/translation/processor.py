"""
File: shl/engine/translation/processor.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Provider-independent preprocessing and postprocessing for SHL
    translation requests.

    Coordinates:
        - placeholder protection
        - HTML detection
        - HTML text processing
        - translation execution
        - HTML integrity validation

    Provider selection and provider-specific policy decisions belong
    to the Router.

    This module does not depend on TemplateLocalizer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Pattern

from .html import (
    HTMLDetector,
    HTMLIntegrityError,
    HTMLTextProcessor,
    TranslationIntegrityValidator,
)
from .metadata import TranslationRequest
from .placeholder import (
    PlaceholderIntegrityError,
    PlaceholderProtector,
)


@dataclass(frozen=True)
class ProcessingResult:
    """
    Result of processing a TranslationRequest.

    Attributes:
        text:
            Final translated text after all restoration and validation.
        had_html:
            Whether HTML-like markup was detected in the original text.
        placeholder_count:
            Number of placeholders protected during processing.
    """

    text: str
    had_html: bool
    placeholder_count: int


class TranslationProcessor:
    """
    Process a TranslationRequest around an externally supplied translator.

    The translator is normally supplied by the Router after the Router
    has selected a provider.

    Expected translator interface:

        translator(request: TranslationRequest) -> str

    The processor does not select providers and does not know which
    provider is being used.
    """

    _PROTECTED_TOKEN_RE = re.compile(
        r"^\s*(?:\{[0-9]+_[0-9]+_[0-9]+\}\s*)+$"
    )

    def __init__(
        self,
        translator: Callable[[TranslationRequest], str],
        *,
        placeholder_pattern: str | Pattern[str] | None = None,
        placeholder_matcher: (
            Callable[[str], list[tuple[int, int]]] | None
        ) = None,
    ) -> None:
        if not callable(translator):
            raise TypeError(
                "text_processor must be callable."
            )

        if (
            placeholder_pattern is not None
            and placeholder_matcher is not None
        ):
            raise ValueError(
                "Specify either placeholder_pattern "
                "or placeholder_matcher, not both."
            )

        self._translator = translator

        self._placeholder_pattern = placeholder_pattern
        self._placeholder_matcher = placeholder_matcher

        self._placeholder_protector: (
            PlaceholderProtector | None
        ) = None

        if (
            placeholder_pattern is not None
            or placeholder_matcher is not None
        ):
            self._placeholder_protector = PlaceholderProtector(
                pattern=placeholder_pattern,
                matcher=placeholder_matcher,
            )

    def process(
        self,
        request: TranslationRequest,
        *,
        process_html: bool | None = None,
    ) -> ProcessingResult:
        """
        Process and translate a TranslationRequest.

        The request itself is never modified.

        HTML handling can be controlled explicitly through process_html.
        When process_html is None, HTML is detected automatically.

        Placeholder protection is applied before translation and restored
        afterwards.

        HTML integrity is validated whenever HTML processing is enabled.
        """
        self._validate_request(request)

        text = request.text

        if not text:
            return ProcessingResult(
                text=text,
                had_html=False,
                placeholder_count=0,
            )

        had_html = HTMLDetector.contains_html(text)

        if process_html is None:
            process_html = request.html_format or had_html

        if process_html and had_html:
            translated, placeholder_count = self._process_html(
                request
            )
        else:
            translated, placeholder_count = self._process_plain(
                request
            )

        return ProcessingResult(
            text=translated,
            had_html=had_html,
            placeholder_count=placeholder_count,
        )

    def _create_placeholder_protector(
        self,
    ) -> PlaceholderProtector | None:
        """
        Create a fresh placeholder protector for one translation scope.

        HTML text nodes must not share validation state because each node
        is translated independently.
        """
        if (
            self._placeholder_pattern is None
            and self._placeholder_matcher is None
        ):
            return None

        return PlaceholderProtector(
            pattern=self._placeholder_pattern,
            matcher=self._placeholder_matcher,
        )

    def _process_plain(
        self,
        request: TranslationRequest,
    ) -> tuple[str, int]:
        """
        Translate a normal TranslationRequest.
        """
        protector = self._create_placeholder_protector()

        translation_request = self._prepare_request(
            request,
            protector,
        )

        translated = self._translate(
            translation_request
        )

        if protector is not None:
            protector.validate(translated)
            translated = protector.restore(
                translated
            )

        return (
            translated,
            (
                protector.protected_count()
                if protector is not None
                else 0
            ),
        )

    def _process_html(
        self,
        request: TranslationRequest,
    ) -> tuple[str, int]:
        """
        Translate textual content inside HTML while preserving markup.

        Each textual HTML node receives its own placeholder protection
        scope. This prevents placeholders from one node from being
        incorrectly validated against another node's translation.
        """

        placeholder_count = 0

        def translate_text_node(
            node_text: str,
        ) -> str:
            nonlocal placeholder_count

            node_request = self._copy_request_with_text(
                request,
                node_text,
            )

            protector = self._create_placeholder_protector()

            prepared_request = self._prepare_request(
                node_request,
                protector,
            )

            if (
                protector is not None
                and protector.protected_count() > 0
                and self._contains_only_protected_tokens(
                    prepared_request.text
                )
            ):
                translated = prepared_request.text
            else:
                translated = self._translate(
                    prepared_request
                )

            if protector is not None:
                protector.validate(translated)
                translated = protector.restore(
                    translated
                )

                placeholder_count += (
                    protector.protected_count()
                )

            return translated

        processor = HTMLTextProcessor(
            translate_text_node
        )

        translated_html = processor.process(
            request.text
        )

        TranslationIntegrityValidator.validate_html(
            request.text,
            translated_html,
        )

        return translated_html, placeholder_count

    @classmethod
    def _contains_only_protected_tokens(
        cls,
        text: str,
    ) -> bool:
        """
        Return True when text contains only SHL-generated protected tokens.

        Protected tokens are technical placeholders created by
        PlaceholderProtector. They must never be sent to a translation
        provider as standalone text.
        """
        if not isinstance(text, str) or not text:
            return False

        return bool(
            cls._PROTECTED_TOKEN_RE.fullmatch(text)
        )

    def _prepare_request(
        self,
        request: TranslationRequest,
        protector: PlaceholderProtector | None,
    ) -> TranslationRequest:
        """
        Create the request sent to the translator.

        The original TranslationRequest remains unchanged.
        """
        text = request.text

        if protector is not None:
            text = protector.protect(text)

        return self._copy_request_with_text(
            request,
            text,
        )

    def _translate(
        self,
        request: TranslationRequest,
    ) -> str:
        """
        Execute the externally supplied translation callable.
        """
        translated = self._translator(request)

        if not isinstance(translated, str):
            raise TypeError(
                "translator must return a string."
            )

        return translated

    @staticmethod
    def _copy_request_with_text(
        request: TranslationRequest,
        text: str,
    ) -> TranslationRequest:
        """
        Create a TranslationRequest with only the text replaced.

        All request metadata is preserved.
        """
        return TranslationRequest(
            text=text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            context_type=request.context_type,
            domain=request.domain,
            formality=request.formality,
            honorific=request.honorific,
            glossary=request.glossary,
            glossary_id=request.glossary_id,
            html_format=request.html_format,
            placeholder_pattern=request.placeholder_pattern,
            key=request.key,
            screen=request.screen,
            component=request.component,
            source_id=request.source_id,
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _validate_request(
        request: TranslationRequest,
    ) -> None:
        """
        Validate the incoming TranslationRequest.
        """
        if not isinstance(
            request,
            TranslationRequest,
        ):
            raise TypeError(
                "request must be a TranslationRequest."
            )

        if not isinstance(request.text, str):
            raise TypeError(
                "request.text must be a string."
            )

        if not isinstance(request.source_lang, str):
            raise TypeError(
                "request.source_lang must be a string."
            )

        if not isinstance(request.target_lang, str):
            raise TypeError(
                "request.target_lang must be a string."
            )

        if not isinstance(request.html_format, bool):
            raise TypeError(
                "request.html_format must be a boolean."
            )

        if not isinstance(request.metadata, dict):
            raise TypeError(
                "request.metadata must be a dictionary."
            )


def process_translation(
    request: TranslationRequest,
    translator: Callable[[TranslationRequest], str],
    *,
    process_html: bool | None = None,
    placeholder_pattern: str | Pattern[str] | None = None,
    placeholder_matcher: (
        Callable[[str], list[tuple[int, int]]] | None
    ) = None,
) -> str:
    """
    Convenience wrapper around TranslationProcessor.

    Returns only the final translated text.
    """
    processor = TranslationProcessor(
        translator,
        placeholder_pattern=placeholder_pattern,
        placeholder_matcher=placeholder_matcher,
    )

    return processor.process(
        request,
        process_html=process_html,
    ).text


__all__ = [
    "ProcessingResult",
    "TranslationProcessor",
    "process_translation",
]
