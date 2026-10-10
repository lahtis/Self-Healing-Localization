"""
File: shl/engine/language_detection/providers/deepl.py
Author: Tuomas Lähteenmäki
Version: 0.3.1
License: MIT
Description:
    DeepL language detection adapter for SHL.

    DeepL has no dedicated detection endpoint. Detection is derived
    from /v2/translate by sending the text with target_lang equal to
    the source language we already know, then reading the
    `detected_source_language` field from the response. The translated
    output itself is discarded.

    Using source_lang as target_lang avoids introducing an arbitrary
    language that could conflict with the input. DeepL still performs
    its own detection and reports the result.

    All outbound HTTP goes through safe_urlopen for SSRF prevention,
    redirect validation, and response size limits.
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

DEEPL_DETECTION_TIMEOUT = 15


class DeepLDetectionAdapter(LanguageDetectionProvider):
    """DeepL language detection adapter.

    DeepL does not expose a detection endpoint, so this adapter uses
    the translate endpoint with target_lang set to the known source
    language and reads the detected source language from the response.
    The translated text is discarded.

    The detected language is reported with score=None because DeepL
    does not provide a confidence value.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_env_value("DEEPL_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DeepL API key must be provided as parameter or "
                "set as DEEPL_API_KEY"
            )

        self.api_key = self.api_key.strip()

        # Match the same Free vs Pro endpoint selection used by the
        # translation adapter.
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2"
        else:
            self.base_url = "https://api.deepl.com/v2"

        logger.debug(
            "DeepLDetectionAdapter initialized (api_key=%s)",
            self._mask_credential(self.api_key),
        )

    @property
    def name(self) -> str:
        """Return the unique provider name."""
        return "deepl"

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
            source_lang: Known source language, used as target_lang
                for the DeepL translate request. Required — without
                it there is no sensible target language to pick.
            timeout: Optional override for the network timeout, in
                seconds. When None, DEEPL_DETECTION_TIMEOUT is used.

        Returns:
            List containing exactly one LanguageDetectionResult.
        """
        if not isinstance(text, str) or not text.strip():
            raise InvalidRequestError(
                "Text must be a non-empty string."
            )

        if not source_lang:
            raise InvalidRequestError(
                "DeepL detection requires a known source language."
            )

        effective_timeout = (
            timeout
            if timeout is not None
            else DEEPL_DETECTION_TIMEOUT
        )

        payload = self.build_request(text, source_lang)
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
        """Build the DeepL translate request payload.

        target_lang equals source_lang. DeepL still detects the actual
        source language and reports it in the response, and using the
        known source as target avoids an arbitrary language choice.

        The base class signature allows source_lang to be omitted for
        interface compatibility. DeepL requires it, so a None value is
        rejected here rather than silently picking a language.
        """
        if not source_lang:
            raise InvalidRequestError(
                "DeepL detection requires a known source language."
            )

        return {
            "text": [text],
            "target_lang": source_lang.upper(),
        }

    def _call_api(
        self,
        payload: dict[str, Any],
        timeout: float = DEEPL_DETECTION_TIMEOUT,
    ) -> dict[str, Any]:
        """Execute the DeepL translate request."""
        url = f"{self.base_url}/translate"
        request_data = json.dumps(payload).encode("utf-8")

        logger.debug(
            "DeepL detection request to %s (timeout=%s)",
            url,
            timeout,
        )

        request = Request(
            url,
            data=request_data,
            headers={
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"SHL-Client/{SHL_VERSION}",
                "Accept": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=timeout) as response:
            raw = read_limited_response(response, MAX_RESPONSE_BYTES)

        try:
            raw_response = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafeHTTPError(
                f"DeepL response was not valid UTF-8: {exc}",
                kind="invalid_response",
            ) from exc

        try:
            parsed_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise SafeHTTPError(
                f"DeepL response was not valid JSON: {exc}",
                kind="invalid_response",
            ) from exc

        if not isinstance(parsed_response, dict):
            raise ValueError(
                "DeepL API returned an invalid response."
            )

        return parsed_response

    def _parse_response(
        self,
        response: dict[str, Any],
    ) -> list[LanguageDetectionResult]:
        """Convert the DeepL translate response into a detection result.

        Only the `detected_source_language` field is used. The
        translated text is discarded.
        """
        translations = response.get("translations", [])

        if not isinstance(translations, list) or not translations:
            raise ValueError(
                "DeepL API returned no translations."
            )

        first = translations[0]

        if not isinstance(first, dict):
            raise ValueError(
                "DeepL API returned an invalid translation entry."
            )

        detected = first.get("detected_source_language")

        if not isinstance(detected, str) or not detected.strip():
            raise ValueError(
                "DeepL API response missing detected_source_language."
            )

        return [
            LanguageDetectionResult(
                language=detected.lower(),
                score=None,
                provider=self.name,
            )
        ]
