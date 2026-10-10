"""
File: shl/engine/errors/parser.py
Author: Tuomas Lähteenmäki
Version: 0.3.0
License: MIT
Description:
    Provider-independent error parser for SHL translation services.

    Parses HTTP responses, provider-specific JSON payloads, and
    exceptions using declarative provider definitions. Normalizes
    different provider error formats into the common SHL
    NormalizedError model.

    Provider-specific parsing logic is intentionally excluded from
    this module. Provider differences are defined externally through
    provider configuration mappings.

    A successful provider response returns None. Error responses are
    normalized into NormalizedError instances.
"""

import json
import socket
import ssl
import urllib.error
from typing import Any, Mapping, Optional, Sequence, Union

from .codes import (
    ACCESS_DENIED,
    ALREADY_EXISTS,
    API_NOT_FOUND,
    AUTH_BLOCKED,
    AUTH_EXPIRED,
    AUTH_FAILED,
    INVALID_CONTENT_TYPE,
    INVALID_REQUEST,
    INVALID_RESPONSE,
    LANG_PAIR_UNSUPPORTED,
    LANG_UNSUPPORTED,
    METHOD_NOT_ALLOWED,
    NETWORK_ERROR,
    NOT_FOUND,
    QUOTA_EXCEEDED,
    RATE_LIMIT_EXCEEDED,
    REQUEST_TOO_LONG,
    RESPONSE_TOO_LARGE,
    SECURITY_VIOLATION,
    SERVICE_UNAVAILABLE,
    TEXT_TOO_LONG,
    TIMEOUT,
    UNKNOWN_ERROR,
)
from .models import NormalizedError


DEFAULT_HTTP_CODES = {
    400: INVALID_REQUEST,
    401: AUTH_FAILED,
    403: ACCESS_DENIED,
    404: NOT_FOUND,
    405: METHOD_NOT_ALLOWED,
    408: TIMEOUT,
    409: ALREADY_EXISTS,
    413: TEXT_TOO_LONG,
    414: REQUEST_TOO_LONG,
    429: RATE_LIMIT_EXCEEDED,
    500: SERVICE_UNAVAILABLE,
    502: SERVICE_UNAVAILABLE,
    503: SERVICE_UNAVAILABLE,
    504: SERVICE_UNAVAILABLE,
}

# Maps SafeHTTPError.kind values to provider-independent SHL codes.
# String values avoid a dependency on the HTTP utility module.
HTTP_EXCEPTION_CODES = {
    "timeout": TIMEOUT,
    "transport": NETWORK_ERROR,
    "network": NETWORK_ERROR,
    "http_error": NETWORK_ERROR,
    "security": SECURITY_VIOLATION,
    "security_violation": SECURITY_VIOLATION,
    "response_too_large": RESPONSE_TOO_LARGE,
    "invalid_content_type": INVALID_CONTENT_TYPE,
    "invalid_response": INVALID_RESPONSE,
    "auth_blocked": AUTH_BLOCKED,
    "auth_expired": AUTH_EXPIRED,
    "api_not_found": API_NOT_FOUND,
    "lang_pair_unsupported": LANG_PAIR_UNSUPPORTED,
}


class ErrorParser:
    """Provider-independent parser for translation service errors."""

    def __init__(
        self,
        provider: str,
        config: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.provider = provider
        self.config = dict(config or {})

        self.failure_conditions = tuple(
            self.config.get("failure_conditions", ())
        )

        self.code_paths = tuple(
            self.config.get("code_paths", ())
        )

        self.message_paths = tuple(
            self.config.get("message_paths", ())
        )

        self.error_code_map = dict(
            self.config.get("error_codes", {})
        )

    def parse(
        self,
        response: Any = None,
        *,
        http_status: Optional[int] = None,
        exception: Optional[Exception] = None,
    ) -> Optional[NormalizedError]:
        """
        Parse a provider response into a normalized SHL error.

        Returns None when the response is considered successful.
        """
        if exception is not None:
            return self._parse_exception(
                exception,
                http_status,
            )

        payload = self._decode_payload(response)

        if payload is None:
            # Empty bodies are valid for successful HTTP responses.
            if (
                response is None
                and http_status is not None
                and 200 <= http_status < 400
            ):
                return None

            return self._parse_invalid_response(http_status)

        failure_condition = self._find_failure_condition(payload)
        provider_code = self._find_mapped_error_code(payload)
        provider_error_code = self._find_error_code(payload)
        message = self._find_message(payload)

        if failure_condition is not None:
            normalized_code = self._normalize_failure(
                failure_condition,
                provider_code,
                http_status,
            )

            return self._build_error(
                normalized_code,
                message=message,
                http_status=http_status,
                provider_code=provider_error_code,
                details=payload,
            )

        if http_status is not None and http_status >= 400:
            normalized_code = self._normalize_http_error(
                provider_code,
                http_status,
            )

            return self._build_error(
                normalized_code,
                message=message,
                http_status=http_status,
                provider_code=provider_error_code,
                details=payload,
            )

        if provider_code is not None:
            normalized_code = self._normalize_provider_code(
                provider_code,
            )

            if normalized_code != UNKNOWN_ERROR:
                return self._build_error(
                    normalized_code,
                    message=message,
                    http_status=http_status,
                    provider_code=provider_error_code,
                    details=payload,
                )

        if http_status is not None and 200 <= http_status < 400:
            return None

        return self._parse_invalid_response(
            http_status,
            payload=payload,
        )

    def _build_error(
        self,
        code: str,
        *,
        message: Optional[str],
        http_status: Optional[int],
        provider_code: Optional[str],
        details: Optional[Mapping[str, Any]],
    ) -> NormalizedError:
        """Build a normalized SHL error."""
        return NormalizedError(
            code=code,
            provider=self.provider,
            message=message,
            temporary=self._is_temporary(code),
            retryable=self._is_retryable(code),
            http_status=http_status,
            provider_code=provider_code,
            details=details,
        )

    def _normalize_failure(
        self,
        failure_condition: Mapping[str, Any],
        provider_code: Optional[str],
        http_status: Optional[int],
    ) -> str:
        """
        Normalize a configured failure condition.

        An explicit condition code has highest priority, followed by
        a recognized provider code and finally the HTTP status.
        """
        condition_code = failure_condition.get("code")

        if condition_code is not None:
            return str(condition_code)

        if provider_code is not None:
            normalized = self._normalize_provider_code(provider_code)

            if normalized != UNKNOWN_ERROR:
                return normalized

        if http_status is not None:
            normalized = self._from_http_status_code(http_status)

            if normalized != UNKNOWN_ERROR:
                return normalized

        return UNKNOWN_ERROR

    def _normalize_http_error(
        self,
        provider_code: Optional[str],
        http_status: int,
    ) -> str:
        """
        Prefer a mapped provider response code, then the provider's
        HTTP status mapping, and finally the common HTTP mapping.
        """
        if provider_code is not None:
            normalized = self._normalize_provider_code(provider_code)

            if normalized != UNKNOWN_ERROR:
                return normalized

        return self._from_http_status_code(http_status)

    def _decode_payload(
        self,
        response: Any,
    ) -> Optional[dict[str, Any]]:
        """Decode a response into a mapping."""
        if response is None:
            return None

        if isinstance(response, Mapping):
            return dict(response)

        if isinstance(response, bytes):
            response = response.decode("utf-8", errors="replace")

        if isinstance(response, str):
            if not response.strip():
                return None

            try:
                payload = json.loads(response)
            except (json.JSONDecodeError, ValueError):
                return None

            if isinstance(payload, Mapping):
                return dict(payload)

        return None

    def _find_failure_condition(
        self,
        payload: Mapping[str, Any],
    ) -> Optional[Mapping[str, Any]]:
        """Return the first configured condition that indicates failure."""
        for condition in self.failure_conditions:
            if not isinstance(condition, Mapping):
                continue

            path = condition.get("path")
            operator = condition.get("operator", "eq")

            if not isinstance(path, Sequence) or isinstance(
                path,
                (str, bytes),
            ):
                continue

            value = self._get_path(payload, path)

            if self._condition_matches(
                value,
                operator,
                condition.get("value"),
            ):
                return condition

        return None

    @staticmethod
    def _condition_matches(
        value: Any,
        operator: str,
        expected: Any,
    ) -> bool:
        """Evaluate a declarative failure condition."""
        if operator == "exists":
            return value is not None

        if operator == "not_exists":
            return value is None

        if operator == "eq":
            return value == expected

        if operator == "ne":
            return value != expected

        if operator == "in":
            if isinstance(expected, (set, frozenset, tuple, list)):
                return value in expected
            return False

        if operator == "not_in":
            if isinstance(expected, (set, frozenset, tuple, list)):
                return value not in expected
            return False

        return False

    def _find_error_code(
        self,
        payload: Mapping[str, Any],
    ) -> Optional[str]:
        """Find the first provider error code from configured paths."""
        value = self._find_value(payload, self.code_paths)

        if value is None:
            return None

        if isinstance(value, (str, int, float)):
            return str(value)

        return None

    def _find_mapped_error_code(
        self,
        payload: Mapping[str, Any],
    ) -> Optional[str]:
        """
        Find the first provider code that has a configured SHL mapping.

        This prevents ordinary status fields such as MyMemory's
        responseStatus=200 from being interpreted as provider errors.
        """
        for path in self.code_paths:
            value = self._get_path(payload, path)

            if value is None:
                continue

            candidates = [value]

            if isinstance(value, str):
                coerced = self._coerce_code(value)

                if coerced != value:
                    candidates.append(coerced)

            for candidate in candidates:
                try:
                    if candidate in self.error_code_map:
                        return str(candidate)
                except TypeError:
                    continue

        return None

    def _find_message(
        self,
        payload: Mapping[str, Any],
    ) -> Optional[str]:
        """Find an error message using configured paths."""
        value = self._find_value(payload, self.message_paths)

        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, (list, tuple)):
            return "; ".join(str(item) for item in value)

        if isinstance(value, Mapping):
            return json.dumps(value, ensure_ascii=False)

        return str(value)

    def _find_value(
        self,
        payload: Mapping[str, Any],
        paths: Sequence[Sequence[str]],
    ) -> Any:
        """Return the first value found from configured paths."""
        for path in paths:
            value = self._get_path(payload, path)

            if value is not None:
                return value

        return None

    @staticmethod
    def _get_path(
        payload: Mapping[str, Any],
        path: Sequence[str],
    ) -> Any:
        """Read a nested value from a mapping."""
        current: Any = payload

        for key in path:
            if not isinstance(current, Mapping):
                return None

            if key not in current:
                return None

            current = current[key]

        return current

    def _normalize_provider_code(
        self,
        provider_code: Union[str, int],
    ) -> str:
        """Map a provider-specific code to an SHL error code."""
        provider_code_str = str(provider_code)

        normalized = self.error_code_map.get(provider_code_str)

        if normalized is not None:
            return normalized

        coerced = self._coerce_code(provider_code_str)

        try:
            normalized = self.error_code_map.get(coerced)
        except TypeError:
            normalized = None

        if normalized is not None:
            return normalized

        return UNKNOWN_ERROR

    @staticmethod
    def _coerce_code(value: Any) -> Any:
        """Convert numeric string codes to integers when possible."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    def _from_http_status_code(
        self,
        http_status: Optional[int],
    ) -> str:
        """
        Map an HTTP status using the provider configuration first.

        Provider error mappings may use integer or string keys.
        The generic HTTP mapping is only a fallback.
        """
        if http_status is None:
            return UNKNOWN_ERROR

        provider_code = self.error_code_map.get(http_status)

        if provider_code is None:
            provider_code = self.error_code_map.get(str(http_status))

        if provider_code is not None:
            return provider_code

        return DEFAULT_HTTP_CODES.get(
            http_status,
            UNKNOWN_ERROR,
        )

    def _parse_invalid_response(
        self,
        http_status: Optional[int],
        payload: Optional[Mapping[str, Any]] = None,
    ) -> NormalizedError:
        """Create an error for an invalid or undecodable response."""
        if http_status is not None and http_status >= 400:
            code = self._from_http_status_code(http_status)

            if code == UNKNOWN_ERROR:
                code = INVALID_RESPONSE
        else:
            code = INVALID_RESPONSE

        return self._build_error(
            code,
            message="Invalid or empty provider response.",
            http_status=http_status,
            provider_code=None,
            details=payload,
        )

    def _parse_exception(
        self,
        exception: Exception,
        http_status: Optional[int],
    ) -> NormalizedError:
        """Normalize an exception into an SHL error."""
        kind = getattr(exception, "kind", None)
        exception_status = getattr(exception, "status_code", None)
        response_body = getattr(exception, "response_body", None)

        if isinstance(exception, urllib.error.HTTPError):
            http_status = exception.code

            try:
                response_body = exception.read()
            except (OSError, ValueError):
                response_body = None

            return self._parse_http_exception(
                exception,
                http_status,
                response_body,
            )

        if http_status is None and isinstance(exception_status, int):
            http_status = exception_status

        if kind == "http_status":
            return self._parse_http_exception(
                exception,
                http_status,
                response_body,
            )

        if isinstance(kind, str) and kind in HTTP_EXCEPTION_CODES:
            code = HTTP_EXCEPTION_CODES[kind]

            return self._build_error(
                code,
                message=str(exception) or None,
                http_status=http_status,
                provider_code=None,
                details={
                    "exception_type": type(exception).__name__,
                    "kind": kind,
                },
            )

        code = self._exception_to_code(exception)

        if (
            http_status is not None
            and http_status >= 400
            and code == UNKNOWN_ERROR
        ):
            code = self._from_http_status_code(http_status)

        return self._build_error(
            code,
            message=str(exception) or None,
            http_status=http_status,
            provider_code=None,
            details={
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )

    def _parse_http_exception(
        self,
        exception: Exception,
        http_status: Optional[int],
        response_body: Any,
    ) -> NormalizedError:
        """
        Parse an HTTP exception using the provider's response and
        HTTP status mappings while preserving diagnostic details.
        """
        payload = self._decode_payload(response_body)

        if payload is not None:
            parsed_error = self.parse(
                payload,
                http_status=http_status,
            )

            if parsed_error is not None:
                return self._build_error(
                    parsed_error.code,
                    message=(
                        parsed_error.message
                        or str(exception)
                        or None
                    ),
                    http_status=(
                        parsed_error.http_status
                        if parsed_error.http_status is not None
                        else http_status
                    ),
                    provider_code=parsed_error.provider_code,
                    details={
                        "response": payload,
                        "exception_type": type(exception).__name__,
                        "exception_message": str(exception),
                        "kind": "http_status",
                    },
                )

        # Use the provider's HTTP mapping before generic defaults.
        code = self._from_http_status_code(http_status)

        if code == UNKNOWN_ERROR:
            code = INVALID_RESPONSE

        return self._build_error(
            code,
            message=str(exception) or None,
            http_status=http_status,
            provider_code=None,
            details={
                "response": response_body,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "kind": "http_status",
            },
        )

    @staticmethod
    def _exception_to_code(exception: Exception) -> str:
        """Map common Python exceptions to SHL error codes."""
        if isinstance(exception, (TimeoutError, socket.timeout)):
            return TIMEOUT

        if isinstance(exception, ssl.SSLError):
            return NETWORK_ERROR

        if isinstance(exception, urllib.error.HTTPError):
            return DEFAULT_HTTP_CODES.get(
                exception.code,
                UNKNOWN_ERROR,
            )

        if isinstance(exception, urllib.error.URLError):
            reason = exception.reason

            if isinstance(reason, (TimeoutError, socket.timeout)):
                return TIMEOUT

            if isinstance(reason, ssl.SSLError):
                return NETWORK_ERROR

            return NETWORK_ERROR

        if isinstance(exception, ConnectionError):
            return NETWORK_ERROR

        name = type(exception).__name__.lower()
        message = str(exception).lower()
        combined = f"{name} {message}"

        if "security_violation" in combined:
            return SECURITY_VIOLATION

        if "response_too_large" in combined:
            return RESPONSE_TOO_LARGE

        if "invalid_content_type" in combined:
            return INVALID_CONTENT_TYPE

        if "api_not_found" in combined:
            return API_NOT_FOUND

        if "lang_pair_unsupported" in combined:
            return LANG_PAIR_UNSUPPORTED

        if (
            "auth_blocked" in combined
            or "account blocked" in combined
        ):
            return AUTH_BLOCKED

        if (
            "auth_expired" in combined
            or "token expired" in combined
            or "credential expired" in combined
        ):
            return AUTH_EXPIRED

        if "timeout" in combined or "timed out" in combined:
            return TIMEOUT

        if "connection" in name or "connect" in name:
            return NETWORK_ERROR

        if "auth" in name or "authentication" in combined:
            return AUTH_FAILED

        if "access denied" in combined or "permission" in name:
            return ACCESS_DENIED

        if "rate" in combined and "limit" in combined:
            return RATE_LIMIT_EXCEEDED

        if "quota" in combined:
            return QUOTA_EXCEEDED

        if "text" in combined and "long" in combined:
            return TEXT_TOO_LONG

        if "request" in combined and "long" in combined:
            return REQUEST_TOO_LONG

        if "method" in combined and "allowed" in combined:
            return METHOD_NOT_ALLOWED

        if "already" in combined and "exist" in combined:
            return ALREADY_EXISTS

        if (
            "language pair" in combined
            and (
                "unsupported" in combined
                or "not supported" in combined
            )
        ):
            return LANG_PAIR_UNSUPPORTED

        if "api" in combined and "not found" in combined:
            return API_NOT_FOUND

        if "language" in combined and (
            "unsupported" in combined
            or "not supported" in combined
        ):
            return LANG_UNSUPPORTED

        if "not found" in combined:
            return NOT_FOUND

        return UNKNOWN_ERROR

    @staticmethod
    def _is_temporary(code: str) -> bool:
        """Return whether an error is considered temporary."""
        return code in {
            RATE_LIMIT_EXCEEDED,
            QUOTA_EXCEEDED,
            NETWORK_ERROR,
            SERVICE_UNAVAILABLE,
            TIMEOUT,
        }

    @staticmethod
    def _is_retryable(code: str) -> bool:
        """Return whether an error can normally be retried."""
        return code in {
            RATE_LIMIT_EXCEEDED,
            NETWORK_ERROR,
            SERVICE_UNAVAILABLE,
            TIMEOUT,
        }
