"""
File: shl/engine/language_detection/providers/detect_language.py
Author: Tuomas Lähteenmäki
Version: 0.3.1
License: MIT
Description:
    Detect Language API adapter for SHL language detection.

# Known issue: detectlanguage returns only top-3 candidates, so
# target languages tied at the low score (e.g. 'dan' at 0.0679
# alongside 'ita', 'swe') are not visible in the result. Revisit
# when a second detection provider is added — may want a shared
# "short text skip" heuristic in the router.
"""

import json
import logging
from typing import Any

from urllib.request import Request
from shl.utils.safe_http import safe_urlopen as urlopen

from shl.utils.safe_http_common import (
    SafeHTTPError,
    MAX_RESPONSE_BYTES,
    read_limited_response,
)

from shl._version import __version__ as SHL_VERSION
from shl.utils.env_loader import get_env_value
from shl.engine.translation.exceptions import InvalidRequestError

from .base import (
    LanguageDetectionProvider,
    LanguageDetectionResult,
)


logger = logging.getLogger(__name__)

DETECTLANGUAGE_TIMEOUT = 15
DETECTLANGUAGE_URL = "https://ws.detectlanguage.com/v3/detect"


class DetectLanguageAdapter(LanguageDetectionProvider):
    """Detect Language API adapter.

    Provides language detection through the Detect Language API
    and converts provider responses into SHL
    LanguageDetectionResult objects.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_env_value(
            "DETECTLANGUAGE_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "Detect Language API key must be provided as parameter "
                "or set as DETECTLANGUAGE_API_KEY"
            )

        self.api_key = self.api_key.strip()

        logger.debug(
            "DetectLanguageAdapter initialized (api_key=%s)",
            self._mask_credential(self.api_key),
        )

    @property
    def name(self) -> str:
        """Return the unique provider name."""
        return "detectlanguage"

    @property
    def supported_features(self) -> list[str]:
        """Return optional features supported by this provider."""
        return []

    def detect(
        self,
        text: str,
        source_lang: str | None = None,
        timeout: float | None = None,
    ) -> list[LanguageDetectionResult]:
        """Detect the language of the supplied text.

        Args:
            text: Text whose language should be detected.
            source_lang: Ignored. Present for interface compatibility
                with providers that require it (e.g. DeepL).
            timeout: Optional override for the network timeout, in
                seconds. When None, DETECTLANGUAGE_TIMEOUT is used.

        Returns:
            List of LanguageDetectionResult objects.
        """
        if not isinstance(text, str) or not text.strip():
            raise InvalidRequestError(
                "Text must be a non-empty string."
            )

        effective_timeout = (
            timeout if timeout is not None else DETECTLANGUAGE_TIMEOUT
        )

        payload = self.build_request(text)
        response = self._call_api(
            payload,
            timeout=effective_timeout,
        )

        return self._parse_response(response)

    def build_request(
        self,
        text: str,
        source_lang: str | None = None,
    ) -> dict[str, Any]:
        """Build the Detect Language API request payload.

        Args:
            text: Text to analyze.
            source_lang: Ignored. Present for interface compatibility.

        Returns:
            Provider-specific request payload.
        """
        return {
            "q": text,
        }

    def _call_api(
        self,
        payload: dict[str, Any],
        timeout: float = DETECTLANGUAGE_TIMEOUT,
    ) -> list[dict[str, Any]]:
        """Execute the Detect Language API request.

        Args:
            payload: Provider-specific request payload.
            timeout: Network timeout in seconds.

        Returns:
            Raw decoded provider response.
        """
        request_data = json.dumps(payload).encode("utf-8")

        logger.debug(
            "Detect Language request to %s (timeout=%s)",
            DETECTLANGUAGE_URL,
            timeout,
        )

        request = Request(
            DETECTLANGUAGE_URL,
            data=request_data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"SHL-Client/{SHL_VERSION}",
                "Accept": "application/json",
            },
            method="POST",
        )

        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw = read_limited_response(response, MAX_RESPONSE_BYTES)

        try:
            raw_response = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafeHTTPError(
                f"Detect Language response was not valid UTF-8: {exc}",
                kind="invalid_response",
            ) from exc

        parsed_response = json.loads(raw_response)

        if not isinstance(parsed_response, list):
            raise ValueError(
                "Detect Language API returned an invalid response."
            )

        return parsed_response

    def _parse_response(
        self,
        response: list[dict[str, Any]],
    ) -> list[LanguageDetectionResult]:
        """Convert the Detect Language response into SHL results.

        Args:
            response: Raw Detect Language API response.

        Returns:
            List of LanguageDetectionResult objects.
        """
        results: list[LanguageDetectionResult] = []

        for item in response:
            if not isinstance(item, dict):
                continue

            language = item.get("language")

            if not language:
                continue

            score = item.get("score")

            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = None

            results.append(
                LanguageDetectionResult(
                    language=str(language),
                    score=score,
                    provider=self.name,
                )
            )

        if not results:
            raise ValueError(
                "Detect Language API returned no language detections."
            )

        return results
