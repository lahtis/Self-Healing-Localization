"""
File: detect_language.py
Author: Tuomas Lähteenmäki
Version: 0.2.15
License: MIT
Description:
    Detect Language API adapter for SHL language detection.
"""

import json
import logging
from typing import Any, Dict, List

from urllib.request import Request, urlopen

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
    """
    Detect Language API adapter.

    Provides language detection through the Detect Language API
    and converts provider responses into SHL
    LanguageDetectionResult objects.
    """

    def __init__(self, api_key=None):
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
            "DetectLanguageAdapter initialized "
            "(api_key=%s)",
            self._mask_credential(self.api_key),
        )

    @property
    def name(self) -> str:
        """
        Return the unique provider name.
        """
        return "detectlanguage"

    @property
    def supported_features(self) -> List[str]:
        """
        Return optional features supported by this provider.
        """
        return []

    def detect(
        self,
        text: str,
    ) -> List[LanguageDetectionResult]:
        """
        Detect the language of the supplied text.

        Args:
            text: Text whose language should be detected.

        Returns:
            List of LanguageDetectionResult objects.
        """
        if not isinstance(text, str) or not text.strip():
            raise InvalidRequestError(
                "Text must be a non-empty string."
            )

        payload = self.build_request(text)
        response = self._call_api(payload)

        return self._parse_response(response)

    def build_request(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """
        Build the Detect Language API request payload.

        Args:
            text: Text to analyze.

        Returns:
            Provider-specific request payload.
        """
        return {
            "q": text,
        }

    def _call_api(
        self,
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Execute the Detect Language API request.

        Args:
            payload: Provider-specific request payload.

        Returns:
            Raw decoded provider response.
        """
        request_data = json.dumps(payload).encode("utf-8")

        logger.debug(
            "Detect Language request to %s",
            DETECTLANGUAGE_URL,
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
            timeout=DETECTLANGUAGE_TIMEOUT,
        ) as response:
            raw_response = response.read().decode("utf-8")

        parsed_response = json.loads(raw_response)

        if not isinstance(parsed_response, list):
            raise ValueError(
                "Detect Language API returned an invalid response."
            )

        return parsed_response

    def _parse_response(
        self,
        response: List[Dict[str, Any]],
    ) -> List[LanguageDetectionResult]:
        """
        Convert the Detect Language response into SHL results.

        Args:
            response: Raw Detect Language API response.

        Returns:
            List of LanguageDetectionResult objects.
        """
        results: List[LanguageDetectionResult] = []

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
