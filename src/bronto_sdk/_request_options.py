"""Per-request options, their merge, and credential resolution.

A ``RequestOptions`` lets a caller override client-level configuration for a
single call. Credential handling follows a **two-mode** model, chosen once at
client construction and never mixed:

* **Client-bound.** The client was built with a credential; every call
  uses it. Passing a per-request credential is a mode violation and raises.
* **Per-request.** The client was built *without* a credential and
  holds none; every call must supply one via ``RequestOptions``, and a call
  that supplies none raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from ._errors import BrontoConfigError


class RequestOptions(TypedDict):
    """Overrides applied to a single request.

    Every field is optional. Non-credential fields fall back to the client
    default when absent.

    Attributes:
        timeout: Per-request timeout in seconds, overriding the client's.
        headers: Extra headers merged over the SDK's, per-request values
            winning on a key clash. **Not a credential channel:** headers here
            are applied verbatim, so a caller who puts an auth header here
            bypasses the credential resolver on purpose.
        api_key: A Bronto API key for this call, emitted as
            ``X-BRONTO-API-KEY``. Valid only on a credential-less
            client; supplying it to a client-bound client raises.
        bearer_token: A JWT bearer token for this call, emitted as
            ``Authorization``. Wins over a per-request ``api_key``. Valid only
            on a credential-less client; supplying it to a client-bound client raises.
        idempotent: Whether the request is safe to retry.
    """

    timeout: NotRequired[float | None]
    headers: NotRequired[Mapping[str, str] | None]
    api_key: NotRequired[str | None]
    bearer_token: NotRequired[str | None]
    idempotent: NotRequired[bool | None]


class ResolvedOptions(TypedDict):
    """The resolved (non-credential) options: every key is present.

    Attributes:
        timeout: The resolved per-request timeout in seconds, or ``None``.
        headers: The merged extra headers, or ``None`` when none were given.
        idempotent: The resolved idempotency flag, or ``None``.
    """

    timeout: float | None
    headers: Mapping[str, str] | None
    idempotent: bool | None


@dataclass(frozen=True)
class ResolvedCredential:
    """The single credential chosen for a request.

    Exactly one scheme, exactly one value — the shape that makes it impossible
    to send two credentials or to re-litigate scheme precedence downstream.

    Attributes:
        scheme: ``"bearer"`` or ``"api_key"``.
        value: The credential string for that scheme.
    """

    scheme: Literal["bearer", "api_key"]
    value: str


def client_credential(
    *,
    api_key: str | None = None,
    bearer_token: str | None = None,
) -> ResolvedCredential | None:
    """Map a client's constructor credentials to its bound credential.

    Args:
        api_key: The client's API key, if any.
        bearer_token: The client's bearer token, if any. Wins over ``api_key``.

    Returns:
        The single bound :class:`ResolvedCredential`, or ``None`` when the
        client was built without a credential (a credential-less client).
    """
    if bearer_token:
        return ResolvedCredential("bearer", bearer_token)
    if api_key:
        return ResolvedCredential("api_key", api_key)
    return None


def _request_credential(
    per_request: RequestOptions | None,
) -> ResolvedCredential | None:
    """Extract the one credential a request supplies, if any.

    Bearer wins over API key within the request.

    Args:
        per_request: The per-call overrides, or ``None``.

    Returns:
        The request's :class:`ResolvedCredential`, or ``None`` when the request
        supplied no credential field at all.

    Raises:
        BrontoConfigError: If a credential field is present but empty.
    """
    request = per_request or {}
    bearer = request.get("bearer_token")
    api_key = request.get("api_key")
    if bearer:
        return ResolvedCredential("bearer", bearer)
    if api_key:
        return ResolvedCredential("api_key", api_key)
    if "bearer_token" in request or "api_key" in request:
        raise BrontoConfigError(
            "A request credential was supplied but empty. Provide a non-empty "
            "bearer_token or api_key."
        )
    return None


def merge_options(
    client_defaults: RequestOptions,
    per_request: RequestOptions | None,
) -> ResolvedOptions:
    """Merge the non-credential options, per-request winning.

    Args:
        client_defaults: The client-level options.
        per_request: The per-call overrides, or ``None`` for no overrides.

    Returns:
        A fully-resolved ``ResolvedOptions`` (absent values set to ``None``).
    """
    request = per_request or {}

    merged_headers = {
        **(client_defaults.get("headers") or {}),
        **(request.get("headers") or {}),
    }

    request_timeout = request.get("timeout")
    request_idempotent = request.get("idempotent")

    return {
        "timeout": (
            request_timeout
            if request_timeout is not None
            else client_defaults.get("timeout")
        ),
        "headers": merged_headers or None,
        "idempotent": (
            request_idempotent
            if request_idempotent is not None
            else client_defaults.get("idempotent")
        ),
    }


def resolve_credential(
    bound: ResolvedCredential | None,
    per_request: RequestOptions | None,
) -> ResolvedCredential:
    """Resolve the one credential that authenticates a request.

    Implements the two-mode rule:

    * **client-bound:** ``bound`` is set. Every call uses it. Supplying
      a per-request credential is a mode violation and raises — the SDK will not
      guess which of two credentials the caller meant.
    * **credential-less:** ``bound`` is ``None`` — the client holds no
      credential. The request must supply one; a request without one raises.

    Args:
        bound: The client's bound credential (from :func:`client_credential`),
            or ``None`` for a credential-less client.
        per_request: The per-call overrides, or ``None`` for no overrides.

    Returns:
        The single :class:`ResolvedCredential` to send.

    Raises:
        BrontoConfigError: On a mode violation (a per-request credential on a
            client-bound client), when a credential-less client request supplies no
            credential, or when a supplied credential field is present but empty.
    """
    supplied = _request_credential(per_request)

    if bound is not None:
        if supplied is not None:
            raise BrontoConfigError(
                "This client is bound to a credential; do not also pass a "
                "per-request bearer_token or api_key. Build a credential-less "
                "client if you want to authenticate each request separately."
            )
        return bound

    if supplied is None:
        raise BrontoConfigError(
            "This client has no credentials set; every request must supply a "
            "bearer_token or an api_key via RequestOptions."
        )
    return supplied
