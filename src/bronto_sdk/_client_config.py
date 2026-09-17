"""Pure configuration and request-prep helpers shared by both sync and async clients."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ._errors import BrontoConfigError, BrontoConnectionError
from ._regions import rest_base_url
from ._request_options import (
    RequestOptions,
    ResolvedCredential,
    merge_options,
    resolve_credential,
)
from ._transport import build_headers, build_url

_ENV_API_KEY = "BRONTO_API_KEY"
_ENV_REGION = "BRONTO_REGION"
_ENV_BASE_URL = "BRONTO_BASE_URL"


@dataclass(frozen=True)
class PreparedRequest:
    """A single call reduced to the concrete inputs ``httpx`` needs.

    Attributes:
        url: The fully-joined request URL.
        headers: The complete outbound header dict, including auth and source.
        timeout: The resolved per-request timeout in seconds, or ``None`` to
            leave ``httpx`` on its own default.
    """

    url: str
    headers: dict[str, str]
    timeout: float | None


@dataclass(frozen=True)
class EnvConfig:
    """The client configuration read from the environment by ``from_env``.

    Attributes:
        api_key: The ``BRONTO_API_KEY`` value.
        region: The ``BRONTO_REGION`` value, or ``None`` when only a base URL
            was supplied.
        base_url: The ``BRONTO_BASE_URL`` value, or ``None`` when unset.
    """

    api_key: str
    region: str | None
    base_url: str | None


def resolve_base_url(*, region: str | None, base_url: str | None) -> str:
    """Resolve the REST base URL from a region or an explicit base URL.

    Args:
        region: The region slug, or ``None``.
        base_url: An explicit base URL that overrides ``region``, or ``None``.

    Returns:
        The base URL to send requests to.

    Raises:
        BrontoConfigError: When neither ``region`` nor ``base_url`` is given.
    """
    if base_url:
        return base_url
    if region:
        return rest_base_url(region)
    raise BrontoConfigError(
        "No endpoint configured. Pass region= (e.g. 'eu' or 'us') or base_url."
    )


def read_env_config() -> EnvConfig:
    """Read client configuration from the standard Bronto environment variables.

    Requires ``BRONTO_API_KEY`` and at least one of ``BRONTO_BASE_URL`` (which
    wins) or ``BRONTO_REGION``.

    Returns:
        The parsed :class:`EnvConfig`.

    Raises:
        BrontoConfigError: Naming the first missing variable — the API key, or
            the region when no base URL is set either.
    """
    api_key = os.environ.get(_ENV_API_KEY)
    if not api_key:
        raise BrontoConfigError(
            f"{_ENV_API_KEY} is not set. Export it, or construct the client "
            "explicitly with api_key=."
        )
    base_url = os.environ.get(_ENV_BASE_URL) or None
    region = os.environ.get(_ENV_REGION) or None
    if not base_url and not region:
        raise BrontoConfigError(
            f"{_ENV_REGION} is not set. Export it (e.g. 'eu' or 'us'), or set "
            f"{_ENV_BASE_URL}."
        )
    return EnvConfig(api_key=api_key, region=region, base_url=base_url)


def client_default_options(*, timeout: float | None) -> RequestOptions:
    """Map the constructor arguments into the client's default options.

    Args:
        timeout: The client-level timeout in seconds.

    Returns:
        The client's default :class:`RequestOptions`.
    """
    return {"timeout": timeout}


def prepare_request(
    *,
    bound: ResolvedCredential | None,
    defaults: RequestOptions,
    base_url: str,
    path: str,
    options: RequestOptions | None,
) -> PreparedRequest:
    """Reduce a single call to the URL, headers, and timeout ``httpx`` needs.

    Runs the shared decision chain: resolve the one credential (enforcing the
    two-mode rule), merge the non-credential options, build the headers from the
    resolved credential plus the merged header overrides, and join the URL.

    Args:
        bound: The client's bound credential, or ``None`` for a credential-less
            client.
        defaults: The client's default options.
        base_url: The client's resolved base URL.
        path: The request path, absolute-style or bare.
        options: The per-request overrides, or ``None``.

    Returns:
        The :class:`PreparedRequest` for this call.

    Raises:
        BrontoConfigError: On a credential mode violation, a missing credential,
            or an empty supplied credential (via
            :func:`bronto_sdk._request_options.resolve_credential`).
    """
    credential = resolve_credential(bound, options)
    merged = merge_options(defaults, options)
    headers = build_headers(credential, user_overrides=merged["headers"])
    return PreparedRequest(
        url=build_url(base_url, path),
        headers=headers,
        timeout=merged["timeout"],
    )


def wrap_transport_error(exc: Exception) -> BrontoConnectionError:
    """Wrap an ``httpx`` transport failure in a credential-free SDK error.

    Transport-level exceptions carry connection metadata (host, timeout) but no
    request headers, so the wrapped message cannot leak a credential.

    Args:
        exc: The ``httpx`` transport exception that was raised.

    Returns:
        A :class:`bronto_sdk._errors.BrontoConnectionError` chained to ``exc``.
    """
    return BrontoConnectionError(f"Could not reach Bronto: {exc}")
