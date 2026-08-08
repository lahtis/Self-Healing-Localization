"""
File: deepl.py — module for DeepL translation adapter (future).
Author: Tuomas Lähteenmäki
Version: 0.2.0
License: MIT
Description:

"""


from typing import Dict, Any, Optional
from ..metadata import TranslationRequest
from .base import TranslationProvider


class DeepLAdapter(TranslationProvider):
    """
    DeepL translation adapter.

    Supports:
    - text, source_lang, target_lang (all providers)
    - context (built from SHL metadata)
    - formality
    - glossary
    """

    def __init__(
        self,
        api_key: str,
        use_free_api: bool = True,
    ):
        self.api_key = api_key
        self.base_url = (
            "https://api-free.deepl.com/v2" if use_free_api else "https://api.deepl.com/v2"
        )

    @property
    def name(self) -> str:
        return "deepl"

    def translate(self, request: TranslationRequest) -> str:
        payload = self.build_request(request)
        return self._call_api(payload)

    def build_request(self, request: TranslationRequest) -> Dict[str, Any]:
        payload = {
            "text": [request.text],
            "source_lang": request.source_lang.upper(),
            "target_lang": request.target_lang.upper(),
        }

        # Build context from SHL metadata
        context_parts = []
        if request.domain:
            context_parts.append(f"Domain: {request.domain}")
        if request.screen:
            context_parts.append(f"Screen: {request.screen}")
        if request.component:
            context_parts.append(f"Component: {request.component}")
        if request.context_type:
            context_parts.append(f"Type: {request.context_type}")
        if request.key:
            context_parts.append(f"Key: {request.key}")

        if context_parts:
            payload["context"] = " | ".join(context_parts)

        if request.formality:
            payload["formality"] = "less" if request.formality == "informal" else "more"

        # Glossary support (needs glossary_id)
        if request.glossary and "id" in request.glossary:
            payload["glossary_id"] = request.glossary["id"]

        # HTML/XML handling
        if request.html_format:
            payload["tag_handling"] = "html"

        return payload

    def _call_api(self, payload: Dict[str, Any]) -> str:
        # Implementation would use requests or httpx
        # This is just a placeholder
        raise NotImplementedError("DeepL adapter coming soon")
