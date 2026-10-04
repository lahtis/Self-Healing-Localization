"""
File: shl/engine/translation/memory/private_mymemory.py
Author: Tuomas Lähteenmäki
Version: 0.2.17
License: MIT
Description:
    MyMemory.dev memory backend for SHL.

    Provides:
        - MyMemory.dev space creation and lookup
        - Memory storage
        - Memory retrieval by UUID
        - Semantic memory search
"""

import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request
from shl.utils.safe_http import safe_urlopen as urlopen

from shl._version import __version__ as SHL_VERSION
from shl.utils.env_loader import get_env_value
from ...errors.parser import ErrorParser
from ...errors.providers import MYMEMORY_DEV


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


class MyMemoryAlreadyExistsError(MyMemoryError):
    """Raised when a memory already exists in MyMemory.dev."""


class PrivateMyMemoryBackend:
    """Memory backend for the MyMemory.dev API."""

    BASE_URL = "https://api.mymemory.dev/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_key_env: str = "MYMEMORY_DEV_API_KEY",
        space_uuid: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key or get_env_value(api_key_env)
        self.space_uuid = space_uuid
        self.timeout = timeout

        self.error_parser = ErrorParser(
            provider="mymemory_dev",
            config=MYMEMORY_DEV,
        )

        if not self.api_key:
            raise MyMemoryAuthError(
                f"MyMemory.dev {api_key_env} is not configured."
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
        An optional 'spaceId' restricts the search to one space.

        If MyMemory.dev reports ignoredFields, the request is rejected
        instead of silently continuing with an unexpected search scope.
        """
        payload: Dict[str, Any] = {
            "query": query,
        }

        if space_uuid is not None:
            payload["spaceId"] = space_uuid

        if limit is not None:
            payload["limit"] = limit

        data = self._post("/search", payload)

        ignored_fields = data.get("ignoredFields", [])

        if ignored_fields:
            raise MyMemoryValidationError(
                f"MyMemory.dev ignored search fields: {ignored_fields}"
            )

        results = data.get("results", [])

        if not isinstance(results, list):
            raise MyMemoryValidationError(
                "MyMemory.dev returned invalid search results."
            )

        return results

    # ------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------

    def _raise_normalized_error(
        self,
        error: Any,
    ) -> None:
        """
        Convert a normalized SHL error into the existing
        MyMemory.dev backend exception hierarchy.
        """

        if error is None:
            raise MyMemoryHTTPError(
                "MyMemory.dev returned an unknown error."
            )

        message = error.message or (
            f"MyMemory.dev request failed: {error.code}"
        )

        if error.code in {
            "AUTH_FAILED",
            "AUTH_EXPIRED",
            "AUTH_BLOCKED",
        }:
            raise MyMemoryAuthError(message)

        if error.code == "NOT_FOUND":
            raise MyMemoryNotFoundError(message)

        if error.code in {
            "INVALID_REQUEST",
            "TEXT_TOO_LONG",
            "REQUEST_TOO_LONG",
            "METHOD_NOT_ALLOWED",
        }:
            raise MyMemoryValidationError(message)

        if error.code == "ALREADY_EXISTS":
            raise MyMemoryAlreadyExistsError(message)

        raise MyMemoryHTTPError(message)

    # ------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------

    def ensure_space(
        self,
        name: str,
        is_public: bool = False,
    ) -> str:
        """Return an existing space UUID or create the space."""

        if self.space_uuid:
            try:
                space = self.get_space(self.space_uuid)

                if (
                    space.get("name") == name
                    and space.get("isPublic") == is_public
                ):
                    return self.space_uuid

            except MyMemoryNotFoundError:
                pass

        spaces = self.list_spaces()

        matches = [
            space
            for space in spaces
            if (
                space.get("name") == name
                and space.get("isPublic") == is_public
                and space.get("uuid")
            )
        ]

        if len(matches) == 1:
            self.space_uuid = matches[0]["uuid"]
            return self.space_uuid

        if len(matches) > 1:
            raise MyMemoryValidationError(
                f"MyMemory.dev returned multiple spaces named "
                f"'{name}'. Space UUID cannot be resolved uniquely."
            )

        data = self.create_space(
            name=name,
            is_public=is_public,
        )

        space = data.get("space", {})
        uuid = space.get("uuid")

        if not uuid:
            raise MyMemoryValidationError(
                "MyMemory.dev did not return a space UUID."
            )

        self.space_uuid = uuid
        return uuid

    def _get(
        self,
        endpoint: str,
    ) -> Dict[str, Any]:
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

        payload = kwargs.get("json")

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = Request(
            url,
            data=data,
            headers=self.headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                status_code = response.status
                response_body = response.read()

        except HTTPError as error:
            try:
                response_body = error.read()
            except Exception:
                response_body = b""

            response_data = self._decode_json(response_body)

            normalized_error = self.error_parser.parse(
                response_data,
                http_status=error.code,
            )

            self._raise_normalized_error(normalized_error)

        except URLError as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=ConnectionError(
                    f"MyMemory.dev connection failed: {error.reason}"
                ),
            )

            self._raise_normalized_error(normalized_error)

        except TimeoutError as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=error,
            )

            self._raise_normalized_error(normalized_error)

        except OSError as error:
            normalized_error = self.error_parser.parse(
                {},
                exception=error,
            )

            self._raise_normalized_error(normalized_error)

        response_data = self._decode_json(response_body)

        if status_code >= 400:
            normalized_error = self.error_parser.parse(
                response_data,
                http_status=status_code,
            )

            self._raise_normalized_error(normalized_error)

        if not isinstance(response_data, dict):
            normalized_error = self.error_parser.parse(
                response_body,
                http_status=status_code,
            )

            self._raise_normalized_error(normalized_error)

        return response_data

    @staticmethod
    def _decode_json(
        response_body: bytes,
    ) -> Any:
        """Decode a JSON response body."""
        if not response_body:
            return {}

        try:
            return json.loads(
                response_body.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return {}

