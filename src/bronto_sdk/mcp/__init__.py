"""MCP endpoint registry: the URL and auth headers, and nothing else.

For now these are just string and dict helpers so a consumer can stop
hardcoding ``mcp.{region}.bronto.io``.
"""

from __future__ import annotations

from .._auth import credential_header
from .._errors import BrontoConfigError
from .._regions import mcp_url
from .._request_options import client_credential

__all__ = ["auth_headers", "url"]

_MCP_PATH = "/mcp"


def url(region: str | None = None, *, base_url: str | None = None) -> str:
    """Return the MCP endpoint URL for a region, or for an explicit host.

    Precedence mirrors the REST clients' ``region``/``base_url`` handling: an
    explicit ``base_url`` wins.

    Args:
        region: The region slug (e.g. ``"eu"``, ``"us"``), or ``None``.
        base_url: An explicit MCP origin that overrides ``region``, e.g.
            ``"https://mcp.eu.staging.bronto.io"``. The ``/mcp`` path is
            appended. **Exempt from slug validation by design** — it is a full
            URL from a trusted source, so a caller passing an untrusted
            ``base_url`` is passing an untrusted host, deliberately.

    Returns:
        ``https://mcp.{region}.bronto.io/mcp``, or ``{base_url}/mcp``.

    Raises:
        BrontoConfigError: When neither ``region`` nor ``base_url`` is given,
            or when ``region`` is not a valid slug.
    """
    if base_url:
        return f"{base_url.rstrip('/')}{_MCP_PATH}"
    if region:
        return mcp_url(region)
    raise BrontoConfigError(
        "No MCP endpoint configured. Pass region= (e.g. 'eu' or 'us') or base_url."
    )


def auth_headers(
    *,
    api_key: str | None = None,
    bearer_token: str | None = None,
) -> dict[str, str]:
    """Build the authentication header for an MCP session.

    Exactly one credential is emitted; ``bearer_token`` wins when both are
    given. The precedence is not re-implemented here — it is the same
    :func:`~bronto_sdk._request_options.client_credential` the REST clients use.

    Args:
        api_key: A Bronto API key.
        bearer_token: A JWT bearer token, sent verbatim. Wins over ``api_key``.

    Returns:
        A single-entry header dict, ready to hand to the ``httpx`` client the
        MCP transport is built on.

    Raises:
        BrontoConfigError: When neither credential is given, or the one given
            is empty. Fails closed — it never returns an unauthenticated dict.
    """
    credential = client_credential(api_key=api_key, bearer_token=bearer_token)
    if credential is None:
        raise BrontoConfigError(
            "No MCP credential supplied. Pass a non-empty api_key or bearer_token."
        )
    return credential_header(credential.scheme, credential.value)
