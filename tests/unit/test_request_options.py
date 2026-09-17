"""Tests for RequestOptions merging and two-mode credential resolution."""

import pytest

from bronto_sdk import BrontoConfigError
from bronto_sdk._request_options import (
    RequestOptions,
    ResolvedCredential,
    client_credential,
    merge_options,
    resolve_credential,
)


def test_none_per_request_returns_client_defaults():
    defaults: RequestOptions = {"timeout": 30.0}
    merged = merge_options(defaults, None)
    assert merged["timeout"] == 30.0
    assert merged["headers"] is None
    assert merged["idempotent"] is None


def test_merge_does_not_expose_credentials():
    merged = merge_options({"api_key": "k", "bearer_token": "jwt"}, None)
    assert "api_key" not in merged
    assert "bearer_token" not in merged


def test_timeout_precedence_and_zero_is_honoured():
    defaults: RequestOptions = {"timeout": 30.0}
    assert merge_options(defaults, {"timeout": 5.0})["timeout"] == 5.0
    assert merge_options(defaults, {"timeout": 0})["timeout"] == 0


def test_headers_are_merged_per_request_winning():
    defaults: RequestOptions = {"headers": {"X-A": "client", "X-B": "client"}}
    merged = merge_options(defaults, {"headers": {"X-B": "request", "X-C": "request"}})
    assert merged["headers"] == {"X-A": "client", "X-B": "request", "X-C": "request"}


def test_absent_headers_merge_to_none():
    assert merge_options({}, None)["headers"] is None


def test_idempotent_passthrough_and_false_is_honoured():
    assert merge_options({}, {"idempotent": True})["idempotent"] is True
    defaults: RequestOptions = {"idempotent": True}
    assert merge_options(defaults, {"idempotent": False})["idempotent"] is False


def test_client_credential_bearer_wins():
    assert client_credential(api_key="k", bearer_token="jwt") == ResolvedCredential(
        "bearer", "jwt"
    )


def test_client_credential_api_key_only():
    assert client_credential(api_key="k") == ResolvedCredential("api_key", "k")


def test_client_credential_none_is_mode_two():
    assert client_credential() is None
    assert client_credential(api_key="", bearer_token="") is None


CLIENT_BEARER = ResolvedCredential("bearer", "CLIENT_JWT")
CLIENT_KEY = ResolvedCredential("api_key", "CLIENT_KEY")


def test_clientboundclient_uses_bound_credential_when_request_has_none():
    assert resolve_credential(CLIENT_BEARER, None) == CLIENT_BEARER
    assert resolve_credential(CLIENT_KEY, {"timeout": 5.0}) == CLIENT_KEY


@pytest.mark.parametrize(
    "per_request",
    [
        {"api_key": "REQ_KEY"},
        {"bearer_token": "REQ_JWT"},
        {"api_key": "REQ_KEY", "bearer_token": "REQ_JWT"},
    ],
)
def test_clientboundclient_per_request_credential_is_a_mode_violation(per_request):
    # A client bound to a credential must not also accept a per-request one:
    # the SDK will not guess which of two credentials the caller meant.
    with pytest.raises(BrontoConfigError) as excinfo:
        resolve_credential(CLIENT_BEARER, per_request)
    assert "bound to a credential" in str(excinfo.value)


@pytest.mark.parametrize(
    ("per_request", "expected"),
    [
        ({"api_key": "REQ_KEY"}, ResolvedCredential("api_key", "REQ_KEY")),
        ({"bearer_token": "REQ_JWT"}, ResolvedCredential("bearer", "REQ_JWT")),
        # Within one request, bearer beats api_key.
        (
            {"bearer_token": "REQ_JWT", "api_key": "REQ_KEY"},
            ResolvedCredential("bearer", "REQ_JWT"),
        ),
    ],
)
def test_credentiallessclient_uses_the_request_credential(per_request, expected):
    assert resolve_credential(None, per_request) == expected


def test_credentiallessclient_without_a_request_credential_raises():
    with pytest.raises(BrontoConfigError) as excinfo:
        resolve_credential(None, None)
    assert "no credential" in str(excinfo.value)


def test_credentiallessclient_empty_request_credential_fails_closed():
    with pytest.raises(BrontoConfigError) as excinfo:
        resolve_credential(None, {"api_key": ""})
    assert "empty" in str(excinfo.value)


def test_clientboundclient_empty_request_credential_fails_closed():
    # An empty field is still "supplied": it must not be silently ignored and
    # allowed to fall through to the bound credential.
    with pytest.raises(BrontoConfigError) as excinfo:
        resolve_credential(CLIENT_BEARER, {"bearer_token": ""})
    assert "empty" in str(excinfo.value)


def test_none_valued_request_credential_fails_closed():
    with pytest.raises(BrontoConfigError):
        resolve_credential(None, {"api_key": None})
