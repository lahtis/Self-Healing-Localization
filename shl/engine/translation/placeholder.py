"""
File: shl/engine/translation/placeholder.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    Provider-independent placeholder protection for SHL.

    Protects arbitrary placeholder-like spans during translation and
    restores them after translation.

    Placeholder syntax is intentionally not hardcoded. A caller may
    provide a regular expression or a custom matcher.

    This module does not handle HTML, provider selection, routing,
    translation, or AI prompt localization.

Use named placeholders whenever possible, for example {name}, {count}, or {username}.
Preserve all placeholders exactly as they appear in the source text.

Placeholders are technical tokens and must not be translated, modified, removed, reordered, or replaced.
Do not add or remove characters inside a placeholder.
Do not insert spaces inside placeholders.

SHL also supports empty placeholders such as {}.
Empty placeholders must be preserved exactly as {} and must not be converted into a named placeholder or otherwise modified.

For example:
"Hello, {name}" → preserve "{name}"
"Saved: {}" → preserve "{}"
"Clear the {} database" → preserve "{}"

Return the translated text with all placeholders preserved exactly as they appeared in the source text.
> SHL supports an empty placeholder but protects it by converting it into a token that appears technical when sent to the service.


"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Callable, Pattern


class PlaceholderIntegrityError(ValueError):
    """Raised when placeholders are changed, removed, or duplicated."""


class PlaceholderConfigurationError(ValueError):
    """Raised when placeholder configuration is invalid."""


@dataclass(frozen=True)
class PlaceholderMatch:
    """
    Represents one protected placeholder.

    Attributes:
        index:
            Stable index assigned during protection.
        value:
            Original placeholder text.
        token:
            Opaque token inserted into the text.
    """

    index: int
    value: str
    token: str


class PlaceholderProtector:
    """
    Protect and restore arbitrary placeholders.

    The placeholder matcher is supplied by the caller.

    A regular expression can be used:

        protector = PlaceholderProtector(
            pattern=r"\\{[^{}]+\\}"
        )

    A custom matcher can also be used:

        def matcher(text):
            ...

        protector = PlaceholderProtector(
            matcher=matcher
        )

    Protection state belongs to one translation request.

    The generated token contains only:
        - curly braces
        - digits
        - underscores

    No alphabetic characters are used in the token. This helps prevent
    ordinary translation transformations from modifying the token.
    """

    _TOKEN_PREFIX = "{"
    _TOKEN_SUFFIX = "}"

    def __init__(
        self,
        pattern: str | Pattern[str] | None = None,
        matcher: Callable[[str], list[tuple[int, int]]] | None = None,
    ) -> None:
        if pattern is not None and matcher is not None:
            raise PlaceholderConfigurationError(
                "Specify either pattern or matcher, not both."
            )

        if pattern is None and matcher is None:
            raise PlaceholderConfigurationError(
                "A placeholder pattern or matcher is required."
            )

        self._matcher = self._build_matcher(
            pattern,
            matcher,
        )

        self._matches: list[PlaceholderMatch] = []
        self._token_map: dict[str, str] = {}

        self._session_id = str(
            secrets.randbelow(10**12)
        )

    @staticmethod
    def _build_matcher(
        pattern: str | Pattern[str] | None,
        matcher: Callable[[str], list[tuple[int, int]]] | None,
    ) -> Callable[[str], list[tuple[int, int]]]:
        """
        Build a normalized matcher function.
        """
        if matcher is not None:
            if not callable(matcher):
                raise PlaceholderConfigurationError(
                    "matcher must be callable."
                )

            return matcher

        if pattern is None:
            raise PlaceholderConfigurationError(
                "pattern is required."
            )

        try:
            compiled = (
                re.compile(pattern)
                if isinstance(pattern, str)
                else pattern
            )
        except (re.error, TypeError) as exc:
            raise PlaceholderConfigurationError(
                f"Invalid placeholder pattern: {exc}"
            ) from exc

        def regex_matcher(
            text: str,
        ) -> list[tuple[int, int]]:
            return [
                match.span()
                for match in compiled.finditer(text)
            ]

        return regex_matcher

    def find(
        self,
        text: str,
    ) -> list[str]:
        """
        Return all placeholder values found in text.

        The original text is not modified.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        spans = self._get_spans(text)

        return [
            text[start:end]
            for start, end in spans
        ]

    def protect(
        self,
        text: str,
    ) -> str:
        """
        Replace detected placeholders with translation-safe tokens.

        Existing protection state is preserved. This allows multiple
        HTML text nodes to share one PlaceholderProtector instance.

        Use clear() when starting a new translation request.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        spans = self._get_spans(text)

        if not spans:
            return text

        parts: list[str] = []
        cursor = 0

        base_index = len(self._matches)

        for local_index, (start, end) in enumerate(spans):
            if start < cursor:
                raise PlaceholderIntegrityError(
                    "Placeholder matcher returned overlapping spans."
                )

            value = text[start:end]

            if not value:
                raise PlaceholderIntegrityError(
                    "Placeholder matcher returned an empty match."
                )

            index = base_index + local_index
            token = self._make_token(index)

            match = PlaceholderMatch(
                index=index,
                value=value,
                token=token,
            )

            self._matches.append(match)
            self._token_map[token] = value

            parts.append(
                text[cursor:start]
            )
            parts.append(token)

            cursor = end

        parts.append(text[cursor:])

        return "".join(parts)

    def restore(
        self,
        text: str,
    ) -> str:
        """
        Restore all protected placeholders.

        Every protected token must occur exactly once.

        Missing, duplicated, or modified tokens raise
        PlaceholderIntegrityError.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        if not self._matches:
            return text

        self.validate(text)

        restored = text

        for match in self._matches:
            restored = restored.replace(
                match.token,
                match.value,
                1,
            )

        return restored

    def validate(
        self,
        text: str,
    ) -> None:
        """
        Validate placeholder integrity.

        Every protected token must occur exactly once.

        Unknown SHL-generated tokens are also rejected.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        if not self._matches:
            return

        expected_tokens = {
            match.token
            for match in self._matches
        }

        for match in self._matches:
            count = text.count(match.token)

            if count == 0:
                raise PlaceholderIntegrityError(
                    f"Placeholder token missing: {match.value!r}"
                )

            if count != 1:
                raise PlaceholderIntegrityError(
                    f"Placeholder token duplicated: {match.value!r}"
                )

        actual_tokens = set(
            self._find_tokens(text)
        )

        unknown_tokens = (
            actual_tokens - expected_tokens
        )

        if unknown_tokens:
            raise PlaceholderIntegrityError(
                "Unknown placeholder token found: "
                f"{sorted(unknown_tokens)!r}"
            )

    def placeholders(self) -> tuple[str, ...]:
        """
        Return all placeholders currently protected.
        """
        return tuple(
            match.value
            for match in self._matches
        )

    def tokens(self) -> tuple[str, ...]:
        """
        Return all currently active protection tokens.
        """
        return tuple(
            match.token
            for match in self._matches
        )

    def protected_count(self) -> int:
        """
        Return the number of currently protected placeholders.
        """
        return len(self._matches)

    def clear(self) -> None:
        """
        Clear the current protection state.

        This should be called when starting a new translation request.
        """
        self._matches.clear()
        self._token_map.clear()

    def _get_spans(
        self,
        text: str,
    ) -> list[tuple[int, int]]:
        """
        Validate and normalize matcher output.
        """
        try:
            raw_spans = self._matcher(text)
        except Exception as exc:
            raise PlaceholderConfigurationError(
                f"Placeholder matcher failed: {exc}"
            ) from exc

        if raw_spans is None:
            return []

        spans: list[tuple[int, int]] = []

        for span in raw_spans:
            if (
                not isinstance(span, tuple)
                or len(span) != 2
            ):
                raise PlaceholderConfigurationError(
                    "Matcher must return (start, end) tuples."
                )

            start, end = span

            if (
                not isinstance(start, int)
                or not isinstance(end, int)
            ):
                raise PlaceholderConfigurationError(
                    "Placeholder span positions must be integers."
                )

            if start < 0 or end < start:
                raise PlaceholderConfigurationError(
                    "Invalid placeholder span."
                )

            if end > len(text):
                raise PlaceholderConfigurationError(
                    "Placeholder span exceeds text length."
                )

            spans.append(
                (start, end)
            )

        spans.sort()

        previous_end = 0

        for start, end in spans:
            if start < previous_end:
                raise PlaceholderIntegrityError(
                    "Placeholder spans overlap."
                )

            previous_end = end

        return spans

    def _make_token(
        self,
        index: int,
    ) -> str:
        """
        Create a translation-resistant placeholder token.
        """
        random_number = secrets.randbelow(
            10**12
        )

        return (
            f"{self._TOKEN_PREFIX}"
            f"{self._session_id}_"
            f"{index}_"
            f"{random_number}"
            f"{self._TOKEN_SUFFIX}"
        )

    def _find_tokens(
        self,
        text: str,
    ) -> list[str]:
        """
        Find all SHL-generated placeholder tokens in text.
        """
        pattern = (
            re.escape(self._TOKEN_PREFIX)
            + r"\d+_\d+_\d+"
            + re.escape(self._TOKEN_SUFFIX)
        )

        return re.findall(
            pattern,
            text,
        )


def protect_placeholders(
    text: str,
    pattern: str | Pattern[str],
) -> tuple[str, PlaceholderProtector]:
    """
    Convenience function for regex-based placeholder protection.

    Returns:
        A tuple containing the protected text and the protector instance.
    """
    protector = PlaceholderProtector(
        pattern=pattern
    )

    return (
        protector.protect(text),
        protector,
    )


__all__ = [
    "PlaceholderConfigurationError",
    "PlaceholderIntegrityError",
    "PlaceholderMatch",
    "PlaceholderProtector",
    "protect_placeholders",
]
