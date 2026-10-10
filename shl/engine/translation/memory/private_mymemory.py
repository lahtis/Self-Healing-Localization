"""
File: shl/engine/translation/memory/private_mymemory.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    MyMemory.dev memory backend for SHL.

    Provides:
        - MyMemory.dev space creation and lookup
        - Memory storage
        - Memory retrieval by UUID
        - Semantic memory search

    All outbound HTTP goes through safe_urlopen for SSRF prevention,
    redirect validation, and response size limits.
"""

import json
from typing import Any, NoReturn
from urllib.request import Request

from shl.utils.safe_http import safe_urlopen as urlopen
from shl.utils.safe_http_common import (
    MAX_RESPONSE_BYTES,
    SafeHTTPError,
    read_limited_response,
)

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
        api_key: str | None = None,
        api_key_env: str = "MYMEMORY_DEV_API_KEY",
        space_uuid: str | None = None,
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
    def headers(self) -> dict[str, str]:
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
    ) -> dict[str, Any]:
        """Create a MyMemory.dev space."""
        payload = {
            "spaceName": name,
            "isPublic": is_public,
        }

        return self._post("/spaces/create", payload)

    # CHANGED: explicit isinstance check so mypy knows the return type
    # and a malformed response degrades to an empty list.
    def list_spaces(self) -> list[dict[str, Any]]:
        """Return available MyMemory.dev spaces."""
        data = self._get("/spaces")
        spaces = data.get("spaces", [])

        if not isinstance(spaces, list):
            return []

        return spaces

    def get_space(self, uuid: str) -> dict[str, Any]:
        """Return a MyMemory.dev space by UUID."""
        return self._get(f"/spaces/{uuid}")

    # ------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------

    def add_memory(
        self,
        content: str,
        memory_type: str = "note",
        space_uuid: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Add a memory to a MyMemory.dev space."""
        uuid = space_uuid or self.space_uuid

        if not uuid:
            raise ValueError(
                "A space UUID is required to add a memory."
            )

        payload: dict[str, Any] = {
            "content": content,
            "type": memory_type,
            "spaces": [uuid],
        }

        if title is not None:
            payload["title"] = title

        return self._post("/add", payload)

    def get_memory(self, memory_uuid: str) -> dict[str, Any]:
        """Return a MyMemory.dev memory by UUID."""
        return self._get(f"/memories/{memory_uuid}")

    # ------------------------------------------------------------
    # Search
    # ------------------------------------------------------------

    def search(
        self,
        query: str,
        space_uuid: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Perform a semantic search against MyMemory.dev memories."""
        payload: dict[str, Any] = {
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

    # CHANGED: NoReturn — this method always raises, so mypy knows
    # that callers cannot continue past it.
    def _raise_normalized_error(
        self,
        error: Any,
    ) -> NoReturn:
        """Convert a normalized SHL error into the existing
        MyMemory.dev backend exception hierarchy. Always raises.
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

    # CHANGED: NoReturn — this method always raises for the same
    # reason as _raise_normalized_error.
    def _raise_http_error(
        self,
        status_code: int | None,
        response_body: bytes | str | None,
    ) -> NoReturn:
        """Convert an HTTP error into a provider-specific exception.
        Always raises.
        """
        response_data = self._decode_json(response_body)

        if status_code == 409:
            normalized_error = self.error_parser.parse(
                response_data,
                http_status=status_code,
            )

            if (
                normalized_error is not None
                and normalized_error.code == "ALREADY_EXISTS"
            ):
                self._raise_normalized_error(normalized_error)

            raise MyMemoryAlreadyExistsError(
                "MyMemory.dev reports that the memory already exists."
            )

        normalized_error = self.error_parser.parse(
            response_data,
            http_status=status_code,
        )

        self._raise_normalized_error(normalized_error)

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
            # CHANGED: explicit type narrowing so the return type
            # matches the annotation.
            matched_uuid = matches[0].get("uuid")
            if not isinstance(matched_uuid, str) or not matched_uuid:
                raise MyMemoryValidationError(
                    "MyMemory.dev returned a space without a UUID."
                )
            self.space_uuid = matched_uuid
            return matched_uuid

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
        uuid = space.get("uuid") if isinstance(space, dict) else None

        # CHANGED: explicit isinstance narrowing instead of truthiness.
        if not isinstance(uuid, str) or not uuid:
            raise MyMemoryValidationError(
                "MyMemory.dev did not return a space UUID."
            )

        self.space_uuid = uuid
        return uuid

    def _get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Perform an authenticated GET request."""
        return self._request("GET", endpoint)

    def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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

        # CHANGED: declared up front so both branches assign to the
        # same typed variables. Mypy now knows these are int | None
        # and bytes | str | None, not conflicting types.
        status_code: int | None = None
        response_body: bytes | str | None = None

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                status_code = response.status
                response_body = read_limited_response(
                    response,
                    MAX_RESPONSE_BYTES,
                )

        except SafeHTTPError as error:
            status_code = getattr(error, "status_code", None)
            response_body = getattr(error, "response_body", None)

            self._raise_http_error(
                status_code=status_code,
                response_body=response_body,
            )

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

        # mypy knows _raise_* are NoReturn, so reaching this point
        # means the try block succeeded and status_code is int.
        if status_code is None:
            # Defensive: should be unreachable, but keeps mypy happy
            # and fails loudly if it ever happens.
            raise MyMemoryHTTPError(
                "MyMemory.dev returned no HTTP status."
            )

        response_data = self._decode_json(response_body)

        if status_code >= 400:
            self._raise_http_error(
                status_code=status_code,
                response_body=response_body,
            )

        if not isinstance(response_data, dict):
            normalized_error = self.error_parser.parse(
                response_body,
                http_status=status_code,
            )

            self._raise_normalized_error(normalized_error)

        return response_data

    @staticmethod
    def _decode_json(
        response_body: bytes | str | None,
    ) -> dict[str, Any]:
        """Decode a JSON response body safely."""
        if not response_body:
            return {}

        if isinstance(response_body, bytes):
            response_body = response_body.decode(
                "utf-8",
                errors="replace",
            )

        if not isinstance(response_body, str):
            return {}

        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

        return data if isinstance(data, dict) else {}
