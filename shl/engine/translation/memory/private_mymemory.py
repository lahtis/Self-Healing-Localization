"""
File: shl/engine/translation/memory/mymemory.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
License: MIT
Description:
    MyMemory.dev memory backend for SHL.

    Provides:
        - MyMemory.dev space creation and lookup
        - Memory storage
        - Memory retrieval by UUID
        - Semantic memory search
"""

from typing import Any, Dict, List, Optional

import requests

from shl import SHL_VERSION
from shl.utils.env_loader import get_env_value


class MyMemoryError(Exception):
    """Base exception for MyMemory.dev errors."""


class MyMemoryAuthError(MyMemoryError):
    """Raised when MyMemory.dev authentication fails."""


class MyMemoryNotFoundError(MyMemoryError):
    """Raised when a MyMemory.dev resource is not found."""


class MyMemoryValidationError(MyMemoryError):
    """Raised when MyMemory.dev rejects the request payload."""


class MyMemoryHTTPError(MyMemoryError):
    """Raised for unexpected MyMemory.dev HTTP errors."""


class PrivateMyMemoryBacken:
    """Memory backend for the MyMemory.dev API."""

    BASE_URL = "https://api.mymemory.dev/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        space_uuid: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key or get_env_value("MYMEMORY_API_KEY")
        self.space_uuid = space_uuid
        self.timeout = timeout

        if not self.api_key:
            raise MyMemoryAuthError(
                "MYMEMORY_API_KEY is not configured."
            )

    @property
    def headers(self) -> Dict[str, str]:
        """Return HTTP headers used by the MyMemory.dev API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"SHL-Client/{SHL_VERSION}",
        }

    # ------------------------------------------------------------
    # Spaces
    # ------------------------------------------------------------

    def create_space(
        self,
        name: str,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a MyMemory.dev space.

        The deployed API requires /spaces/create and uses
        'spaceName' instead of 'name'.
        """
        payload = {
            "spaceName": name,
            "isPublic": is_public,
        }

        return self._post("/spaces/create", payload)

    def list_spaces(self) -> List[Dict[str, Any]]:
        """Return available MyMemory.dev spaces."""
        data = self._get("/spaces")
        return data.get("spaces", [])

    def get_space(self, uuid: str) -> Dict[str, Any]:
        """Return a MyMemory.dev space by UUID."""
        return self._get(f"/spaces/{uuid}")

    # ------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------

    def add_memory(
        self,
        content: str,
        memory_type: str = "note",
        space_uuid: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a memory to a MyMemory.dev space.

        The deployed API requires /add and expects 'spaces'
        as a list of space UUIDs.
        """
        uuid = space_uuid or self.space_uuid

        if not uuid:
            raise ValueError(
                "A space UUID is required to add a memory."
            )

        payload: Dict[str, Any] = {
            "content": content,
            "type": memory_type,
            "spaces": [uuid],
        }

        if title is not None:
            payload["title"] = title

        return self._post("/add", payload)

    def get_memory(self, memory_uuid: str) -> Dict[str, Any]:
        """Return a memory by UUID."""
        return self._get(f"/memories/{memory_uuid}")

    # ------------------------------------------------------------
    # Search
    # ------------------------------------------------------------

    def search(
        self,
        query: str,
        space_uuid: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform a semantic search against MyMemory.dev memories.

        The deployed API uses POST /search with a 'query' field.
        Search is semantic rather than keyword based.
        """
        payload: Dict[str, Any] = {
            "query": query,
        }

        if space_uuid is not None:
            payload["spaceId"] = space_uuid

        if limit is not None:
            payload["limit"] = limit

        data = self._post("/search", payload)

        return data.get("results", [])

    # ------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Perform an authenticated GET request."""
        return self._request("GET", endpoint)

    def _post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Perform an authenticated POST request."""
        return self._request(
            "POST",
            endpoint,
            json=payload,
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform an authenticated HTTP request."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as error:
            raise MyMemoryHTTPError(
                f"MyMemory.dev request failed: {error}"
            ) from error

        return self._handle_response(response)

    @staticmethod
    def _handle_response(
        response: requests.Response,
    ) -> Dict[str, Any]:
        """Convert an HTTP response into a Python dictionary."""
        if response.status_code in (200, 201):
            try:
                data = response.json()
            except ValueError:
                return {}

            return data if isinstance(data, dict) else {}

        if response.status_code == 401:
            raise MyMemoryAuthError(
                "MyMemory.dev authentication failed."
            )

        if response.status_code == 404:
            raise MyMemoryNotFoundError(
                f"MyMemory.dev resource not found: {response.url}"
            )

        if response.status_code == 400:
            try:
                data = response.json()
            except ValueError:
                data = {}

            issues = data.get("issues")

            if issues:
                raise MyMemoryValidationError(
                    f"MyMemory.dev validation error: {issues}"
                )

            raise MyMemoryValidationError(
                f"MyMemory.dev rejected the request: {data}"
            )

        try:
            data = response.json()
        except ValueError:
            data = response.text

        raise MyMemoryHTTPError(
            f"MyMemory.dev returned HTTP {response.status_code}: {data}"
        )
