# shl/engine/errors/parser.py
"""
File: shl/engine/errors/parser.py
Author: Tuomas Lähteenmäki
Version: 0.2.10
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
from typing import Any, Mapping, Optional, Sequence, Union

from .codes import (
    ACCESS_DENIED,
    AUTH_FAILED,
    INVALID_REQUEST,
    INVALID_RESPONSE,
    LANG_UNSUPPORTED,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    QUOTA_EXCEEDED,
    RATE_LIMIT_EXCEEDED,
    REQUEST_TOO_LONG,
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
    413: TEXT_TOO_LONG,
    414: REQUEST_TOO_LONG,
    429: RATE_LIMIT_EXCEEDED,
    500: SERVICE_UNAVAILABLE,
    502: SERVICE_UNAVAILABLE,
    503: SERVICE_UNAVAILABLE,
    504: SERVICE_UNAVAILABLE,
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
            self.config.get(
                "failure_conditions",
                (),
            )
        )

        self.code_paths = tuple(
            self.config.get(
                "code_paths",
                (),
            )
        )

        self.message_paths = tuple(
            self.config.get(
                "message_paths",
                (),
            )
        )

        self.error_code_map = dict(
            self.config.get(
                "error_codes",
                {},
            )
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
            return self._parse_invalid_response(
                http_status,
            )

        failure_condition = self._find_failure_condition(
            payload,
        )

        provider_code = self._find_mapped_error_code(
            payload,
        )

        provider_error_code = self._find_error_code(
            payload,
        )

        message = self._find_message(
            payload,
        )

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
        a mapped provider code and finally the HTTP status.
        """
        condition_code = failure_condition.get("code")

        if condition_code is not None:
            return str(condition_code)

        if provider_code is not None:
            return self._normalize_provider_code(
                provider_code,
            )

        if http_status is not None:
            return self._from_http_status_code(
                http_status,
            )

        return UNKNOWN_ERROR

    def _normalize_http_error(
        self,
        provider_code: Optional[str],
        http_status: int,
    ) -> str:
        """
        Normalize an HTTP error.

        A known provider-specific code takes priority over the generic
        HTTP status mapping.
        """
        if provider_code is not None:
            normalized = self._normalize_provider_code(
                provider_code,
            )
            if normalized != UNKNOWN_ERROR:
                return normalized

        return self._from_http_status_code(
            http_status,
        )

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
            response = response.decode(
                "utf-8",
                errors="replace",
            )

        if isinstance(response, str):
            try:
                payload = json.loads(response)
            except json.JSONDecodeError:
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
            operator = condition.get(
                "operator",
                "eq",
            )

            if not isinstance(path, Sequence) or isinstance(
                path,
                (str, bytes),
            ):
                continue

            value = self._get_path(
                payload,
                path,
            )

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
        value = self._find_value(
            payload,
            self.code_paths,
        )

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
            value = self._get_path(
                payload,
                path,
            )

            if value is None:
                continue

            candidates = [value]

            if isinstance(value, str):
                coerced = self._coerce_code(value)
                if coerced != value:
                    candidates.append(coerced)

            for candidate in candidates:
                if candidate in self.error_code_map:
                    return str(candidate)

        return None

    def _find_message(
        self,
        payload: Mapping[str, Any],
    ) -> Optional[str]:
        """Find an error message using configured paths."""
        value = self._find_value(
            payload,
            self.message_paths,
        )

        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, (list, tuple)):
            return "; ".join(
                str(item)
                for item in value
            )

        if isinstance(value, Mapping):
            return json.dumps(
                value,
                ensure_ascii=False,
            )

        return str(value)

    def _find_value(
        self,
        payload: Mapping[str, Any],
        paths: Sequence[Sequence[str]],
    ) -> Any:
        """Return the first value found from configured paths."""
        for path in paths:
            value = self._get_path(
                payload,
                path,
            )

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

        normalized = self.error_code_map.get(
            provider_code_str,
        )

        if normalized is not None:
            return normalized

        coerced = self._coerce_code(
            provider_code_str,
        )

        normalized = self.error_code_map.get(
            coerced,
        )

        if normalized is not None:
            return normalized

        return UNKNOWN_ERROR

    @staticmethod
    def _coerce_code(
        value: Any,
    ) -> Any:
        """Convert numeric string codes to integers when possible."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    def _parse_invalid_response(
        self,
        http_status: Optional[int],
        payload: Optional[Mapping[str, Any]] = None,
    ) -> NormalizedError:
        """Create an error for an invalid or undecodable response."""
        if http_status is not None:
            code = self._from_http_status_code(
                http_status,
            )

            if code == UNKNOWN_ERROR:
                code = INVALID_RESPONSE
        else:
            code = INVALID_RESPONSE

        return NormalizedError(
            code=code,
            provider=self.provider,
            message="Invalid or empty provider response.",
            temporary=self._is_temporary(code),
            retryable=self._is_retryable(code),
            http_status=http_status,
            details=payload,
        )

    @staticmethod
    def _from_http_status_code(
        http_status: Optional[int],
    ) -> str:
        """Map an HTTP status code to an SHL error code."""
        if http_status is None:
            return UNKNOWN_ERROR

        return DEFAULT_HTTP_CODES.get(
            http_status,
            UNKNOWN_ERROR,
        )

    def _parse_exception(
        self,
        exception: Exception,
        http_status: Optional[int],
    ) -> NormalizedError:
        """Normalize an exception into an SHL error."""
        code = self._exception_to_code(
            exception,
        )

        return NormalizedError(
            code=code,
            provider=self.provider,
            message=str(exception),
            temporary=self._is_temporary(code),
            retryable=self._is_retryable(code),
            http_status=http_status,
            details={
                "exception_type": type(exception).__name__,
            },
        )

    @staticmethod
    def _exception_to_code(
        exception: Exception,
    ) -> str:
        """Map common exception types to SHL error codes."""
        name = type(exception).__name__.lower()

        if "timeout" in name:
            return TIMEOUT

        if "connection" in name or "connect" in name:
            return SERVICE_UNAVAILABLE

        if "auth" in name and "expired" in name:
            return AUTH_FAILED

        if "auth" in name:
            return AUTH_FAILED

        if "access" in name or "permission" in name:
            return ACCESS_DENIED

        if "rate" in name and "limit" in name:
            return RATE_LIMIT_EXCEEDED

        if "quota" in name:
            return QUOTA_EXCEEDED

        if "text" in name and "long" in name:
            return TEXT_TOO_LONG

        if "request" in name and "long" in name:
            return REQUEST_TOO_LONG

        if "method" in name and "allowed" in name:
            return METHOD_NOT_ALLOWED

        if "not" in name and "found" in name:
            return NOT_FOUND

        if "language" in name and "support" in name:
            return LANG_UNSUPPORTED

        return UNKNOWN_ERROR

    @staticmethod
    def _is_temporary(
        code: str,
    ) -> bool:
        """Return whether an error is considered temporary."""
        return code in {
            RATE_LIMIT_EXCEEDED,
            QUOTA_EXCEEDED,
            SERVICE_UNAVAILABLE,
            TIMEOUT,
        }

    @staticmethod
    def _is_retryable(
        code: str,
    ) -> bool:
        """Return whether an error can normally be retried."""
        return code in {
            RATE_LIMIT_EXCEEDED,
            SERVICE_UNAVAILABLE,
            TIMEOUT,
        }
