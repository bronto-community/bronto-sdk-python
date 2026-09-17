"""Pure request-building and response-parsing helpers.

Every decision the sync and async clients share lives here as a plain function
with no I/O, so a bug is fixed in one place and both clients inherit the fix.
The clients become thin shells: they call :func:`build_url` and
:func:`build_headers` to shape a request, hand it to ``httpx``, then pass the
raw ``httpx`` response through :func:`parse_response`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from ._auth import credential_header, user_agent
from ._errors import BrontoAPIError, error_from_response
from ._request_options import ResolvedCredential

_CONTENT_TYPE = "application/json"


def build_url(base_url: str, path: str) -> str:
    """Join a base URL and a path with exactly one separating slash.

    Works whether ``path`` is absolute-style (``"/search"``) or bare
    (``"monitors/m-1"``), and whether ``base_url`` has a trailing slash.

    Args:
        base_url: The API base URL, e.g. ``https://api.eu.bronto.io``.
        path: The request path, with or without a leading slash.

    Returns:
        The joined URL with a single slash between base and path.
    """
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def build_headers(
    credential: ResolvedCredential,
    *,
    user_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Compose the outbound headers for a request.

    Takes an already-resolved single credential so it is structurally impossible to
    hand this function two credentials and have it silently choose. Later layers win on
    a key clash. Overrides are applied last on purpose - they are an escape hatch for
    headers the SDK does not model.

    Args:
        credential: The single resolved credential to authenticate with.
        user_overrides: Extra headers merged over the SDK's, caller values
            winning on a key clash.

    Returns:
        The complete header dict to send.
    """
    headers: dict[str, str] = {
        "Content-Type": _CONTENT_TYPE,
        "User-Agent": user_agent(),
    }
    headers.update(credential_header(credential.scheme, credential.value))
    if user_overrides:
        headers.update(user_overrides)
    return headers


def parse_response(
    status: int,
    headers: Mapping[str, str] | None,
    body: str | None,
) -> dict[str, object]:
    """Turn a raw HTTP response into a parsed JSON object or an error.

    On a 2xx status the body must be a JSON object; anything else (a non-JSON
    body, or a JSON array/scalar) is a contract violation and raises a
    ``BrontoAPIError`` that preserves the status. On a non-2xx status the right
    ``BrontoAPIError`` subclass is raised via
    :func:`bronto_sdk._errors.error_from_response`, which already degrades
    gracefully on a non-JSON error body.

    Args:
        status: The HTTP status code.
        headers: The response headers.
        body: The raw response body.

    Returns:
        The decoded JSON object on a successful response.

    Raises:
        BrontoAPIError: On any non-2xx status, or on a 2xx response whose body
            is not a JSON object.
    """
    if not 200 <= status <= 299:
        raise error_from_response(status, headers, body)

    try:
        parsed: object = json.loads(body) if body else None
    except (ValueError, TypeError):
        parsed = None

    if not isinstance(parsed, dict):
        raise BrontoAPIError(
            "Bronto returned a successful status with a non-JSON-object body",
            status_code=status,
            body=body,
            headers=headers,
        )

    return {str(key): value for key, value in parsed.items()}  # type: ignore[misc]
