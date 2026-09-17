"""Authentication and identity header construction.

Bronto accepts two schemes: a JWT bearer token (``Authorization``) and an API
key (``X-BRONTO-API-KEY``).
"""

from __future__ import annotations

from typing import Literal

from ._version import VERSION

_API_KEY_HEADER = "X-BRONTO-API-KEY"
_BEARER_HEADER = "Authorization"


def credential_header(
    scheme: Literal["bearer", "api_key"], value: str
) -> dict[str, str]:
    """Build the auth header for an already-resolved single credential.

    Args:
        scheme: ``"bearer"`` or ``"api_key"``.
        value: The credential string for that scheme.

    Returns:
        A single-entry dict with the matching authentication header.
    """
    if scheme == "bearer":
        return {_BEARER_HEADER: value}
    return {_API_KEY_HEADER: value}


def user_agent() -> str:
    """Return the SDK's ``User-Agent`` value.

    Returns:
        ``bronto-sdk-python/<version>``.
    """
    return f"bronto-sdk-python/{VERSION}"
