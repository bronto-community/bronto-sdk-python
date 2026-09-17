"""The exception hierarchy every other module raises.

This module is deliberately dependency-free (stdlib and ``typing`` only): it is
imported by the region and auth helpers, the transport layer, and both clients,
so it must not pull in ``httpx`` or ``pydantic``.

* **No credential may reach an error, ``repr()``, or log line.** Request headers
  are redacted by key name *before* being stored on an error, and neither
  ``__str__`` nor ``__repr__`` ever renders a header value.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

_SENSITIVE_HEADER_KEYS = frozenset(
    {
        "authorization",
        "bearer_token",
        "bronto_api_key",
        "x-bronto-api-key",
        "api_key",
        "token",
    }
)

_REDACTED = "[redacted]"


def _redact_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """Return a copy of ``headers`` with sensitive values replaced.

    Args:
        headers: The response (or request) headers to sanitise. ``None`` is
            treated as an empty mapping.

    Returns:
        A new dict in which any header whose lower-cased name is in
        ``_SENSITIVE_HEADER_KEYS`` has its value replaced with ``[redacted]``.
        The original mapping is never mutated.
    """
    if not headers:
        return {}
    return {
        key: (_REDACTED if key.lower().strip() in _SENSITIVE_HEADER_KEYS else value)
        for key, value in headers.items()
    }


class BrontoError(Exception):
    """Base class for every exception the SDK raises.

    Catching ``BrontoError`` catches everything this SDK can raise, whether it
    originates from configuration, the network, or an API response.
    """


class BrontoConfigError(BrontoError):
    """A configuration problem the SDK can detect without a network call.

    Raised for a missing or malformed environment variable, an unknown or
    region slug, or a request made with no credential available.
    """


class BrontoConnectionError(BrontoError):
    """A transport-level failure with no HTTP response to inspect.

    Wraps ``httpx`` transport exceptions (DNS resolution, TLS handshake,
    connection, and timeout errors) so callers never have to catch an ``httpx``
    type directly.
    """


class BrontoAPIError(BrontoError):
    """A non-2xx HTTP response from the Bronto API.

    Attributes:
        status_code: The HTTP status code of the response.
        correlation_id: Bronto's request correlation id, when the response
            contained one. The single most useful field for a support ticket, so
            it is surfaced in ``str()``.
        details: The human-readable error description from the response, when
            present.
        error_type: The error ``type`` (the HTTP reason phrase, e.g.
            ``"Not Found"``), when present.
        body: The response body.
        headers: The response headers with sensitive values redacted.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        correlation_id: str | None = None,
        details: str | None = None,
        error_type: str | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Initialise the error, redacting headers.

        Args:
            message: The human-readable message passed to ``Exception``.
            status_code: The HTTP status code of the response.
            correlation_id: Bronto's request correlation id, when known.
            details: The response's human-readable description, when present.
            error_type: The error ``type`` field, when present.
            body: The raw response body.
            headers: The response headers.
        """
        super().__init__(message)
        self.status_code = status_code
        self.correlation_id = correlation_id
        self.details = details
        self.error_type = error_type
        self.body = body
        self.headers = _redact_headers(headers)

    @property
    def retryable(self) -> bool:
        """Whether retrying the request could plausibly succeed.

        True for ``429`` and any ``5xx``.

        Returns:
            ``True`` for rate-limit and server errors, ``False`` otherwise.
        """
        return self.status_code == 429 or 500 <= self.status_code <= 599

    def __str__(self) -> str:
        """Render the status code and correlation id.

        Returns:
            The base message with the status code always shown and the
            correlation id appended when known.
        """
        base = super().__str__()
        suffix = f" (HTTP {self.status_code}"
        if self.correlation_id:
            suffix += f", correlation_id={self.correlation_id}"
        suffix += ")"
        return f"{base}{suffix}"


class BrontoBadRequestError(BrontoAPIError):
    """A ``400 Bad Request`` response — the request was malformed or invalid."""


class BrontoAuthenticationError(BrontoAPIError):
    """A ``401 Unauthorized`` response — the credential was missing or invalid."""


class BrontoPermissionError(BrontoAPIError):
    """A ``403 Forbidden`` response — the credential lacks the permission."""


class BrontoNotFoundError(BrontoAPIError):
    """A ``404 Not Found`` response — the resource does not exist."""


class BrontoRateLimitError(BrontoAPIError):
    """A ``429 Too Many Requests`` response — the client is being rate limited.

    Attributes:
        retry_after: Seconds to wait before retrying, parsed from the standard
            ``Retry-After`` header. None`` when absent.
        rate_limit_reset: The value of the ``RateLimit-Reset``. ``None`` when absent.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        correlation_id: str | None = None,
        details: str | None = None,
        error_type: str | None = None,
        body: str | None = None,
        headers: Mapping[str, str] | None = None,
        retry_after: int | None = None,
        rate_limit_reset: int | None = None,
    ) -> None:
        """Initialise the error and record the rate-limit timing headers.

        Args:
            message: The human-readable message.
            status_code: The HTTP status code.
            correlation_id: Bronto's request correlation id.
            details: The response's human-readable description, when present.
            error_type: The response's ``type`` field, when present.
            body: The raw response body.
            headers: The response headers.
            retry_after: Parsed ``Retry-After`` seconds, when the header is set.
            rate_limit_reset: Parsed ``RateLimit-Reset`` value, when present.
        """
        super().__init__(
            message,
            status_code=status_code,
            correlation_id=correlation_id,
            details=details,
            error_type=error_type,
            body=body,
            headers=headers,
        )
        self.retry_after = retry_after
        self.rate_limit_reset = rate_limit_reset


class BrontoServerError(BrontoAPIError):
    """A ``5xx`` response — Bronto failed to process an otherwise valid request."""


_STATUS_MAP: dict[int, type[BrontoAPIError]] = {
    400: BrontoBadRequestError,
    401: BrontoAuthenticationError,
    403: BrontoPermissionError,
    404: BrontoNotFoundError,
    429: BrontoRateLimitError,
}


def _parse_envelope(body: str | None) -> dict[str, object]:
    """Parse Bronto's error envelope from a response body.

    Args:
        body: The raw response body.

    Returns:
        The decoded JSON object when the body is a JSON object, otherwise an
        empty dict. Never raises: a non-JSON or non-object body simply yields
        no envelope fields, and the caller degrades to the raw body.
    """
    if not body:
        return {}
    try:
        parsed: object = json.loads(body)
    except (ValueError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items()}  # type: ignore[misc]


def _message_from(envelope: Mapping[str, object], body: str | None) -> str:
    """Pick the best available human-readable message.

    Prefer the envelope's ``details``, fall back to a ``message`` field, then
    to a bounded snippet of the raw body, then to a generic string.

    Args:
        envelope: The parsed error envelope (possibly empty).
        body: The raw response body, used as a last-resort snippet.

    Returns:
        A non-empty message string safe to store on the exception.
    """
    details = envelope.get("details")
    if isinstance(details, str) and details:
        return details
    message = envelope.get("message")
    if isinstance(message, str) and message:
        return message
    if body:
        return body[:300]
    return "Bronto API request failed"


def _parse_int_header(headers: Mapping[str, str] | None, name: str) -> int | None:
    """Parse an integer-valued header, returning ``None`` when absent or invalid.

    Args:
        headers: The response headers, or ``None``.
        name: The header name to look up (case-insensitive).

    Returns:
        The parsed integer, or ``None`` when the header is missing or not a
        base-10 integer.
    """
    if not headers:
        return None
    for key, value in headers.items():
        if key.lower() == name.lower():
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
    return None


def error_from_response(
    status: int,
    headers: Mapping[str, str] | None,
    body: str | None,
) -> BrontoAPIError:
    """Build the right ``BrontoAPIError`` subclass for a non-2xx response.

    Headers are redacted, so the returned error is safe to log.

    Args:
        status: The HTTP status code of the response.
        headers: The response headers.
        body: The raw response body.

    Returns:
        A ``BrontoAPIError`` (or the matching subclass) describing the failure.
    """
    envelope = _parse_envelope(body)
    message = _message_from(envelope, body)
    correlation = envelope.get("correlation_id")
    error_type = envelope.get("type")
    details = envelope.get("details")
    common: dict[str, object] = {
        "status_code": status,
        "correlation_id": correlation if isinstance(correlation, str) else None,
        "details": details if isinstance(details, str) else None,
        "error_type": error_type if isinstance(error_type, str) else None,
        "body": body,
        "headers": headers,
    }

    if status == 429:
        return BrontoRateLimitError(
            message,
            retry_after=_parse_int_header(headers, "Retry-After"),
            rate_limit_reset=_parse_int_header(headers, "RateLimit-Reset"),
            **common,  # type: ignore[arg-type]
        )

    cls = _STATUS_MAP.get(status)
    if cls is None:
        cls = BrontoServerError if 500 <= status <= 599 else BrontoAPIError
    return cls(message, **common)  # type: ignore[arg-type]
