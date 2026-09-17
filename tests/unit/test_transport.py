"""Tests for the pure transport helpers: URL joining, headers, parsing, etc..."""

import json

import pytest

import bronto_sdk
from bronto_sdk import (
    BrontoAPIError,
    BrontoAuthenticationError,
    BrontoNotFoundError,
    BrontoRateLimitError,
    BrontoServerError,
)
from bronto_sdk._request_options import ResolvedCredential
from bronto_sdk._transport import build_headers, build_url, parse_response

BASE = "https://api.eu.bronto.io"
API_KEY_CRED = ResolvedCredential("api_key", "k")
BEARER_CRED = ResolvedCredential("bearer", "jwt")


@pytest.mark.parametrize(
    ("base", "path", "expected"),
    [
        (BASE, "/search", f"{BASE}/search"),
        (BASE, "monitors/m-1", f"{BASE}/monitors/m-1"),
        (f"{BASE}/", "/search", f"{BASE}/search"),
        (f"{BASE}/", "monitors/m-1", f"{BASE}/monitors/m-1"),
    ],
)
def test_build_url_single_slash_join(base, path, expected):
    assert build_url(base, path) == expected


def test_build_url_never_doubles_the_slash():
    assert "//search" not in build_url(f"{BASE}/", "/search")


def test_build_headers_includes_content_type_and_user_agent():
    headers = build_headers(API_KEY_CRED)
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == f"bronto-sdk-python/{bronto_sdk.VERSION}"


def test_build_headers_api_key_scheme():
    headers = build_headers(API_KEY_CRED)
    assert headers["X-BRONTO-API-KEY"] == "k"
    assert "Authorization" not in headers


def test_build_headers_bearer_scheme():
    headers = build_headers(BEARER_CRED)
    assert headers["Authorization"] == "jwt"
    assert "X-BRONTO-API-KEY" not in headers


def test_build_headers_user_overrides_applied_last():
    headers = build_headers(API_KEY_CRED, user_overrides={"X-BRONTO-SOURCE": "svc"})
    assert headers["X-BRONTO-SOURCE"] == "svc"


def test_build_headers_user_override_can_replace_auth_header():
    headers = build_headers(
        API_KEY_CRED, user_overrides={"X-BRONTO-API-KEY": "override"}
    )
    assert headers["X-BRONTO-API-KEY"] == "override"


def test_parse_response_returns_json_object_on_2xx():
    body = json.dumps({"count": 3, "events": []})
    assert parse_response(200, {}, body) == {"count": 3, "events": []}


def test_parse_response_2xx_non_json_body_raises_preserving_status():
    with pytest.raises(BrontoAPIError) as excinfo:
        parse_response(200, {}, "not json")
    assert excinfo.value.status_code == 200


def test_parse_response_2xx_json_array_raises():
    with pytest.raises(BrontoAPIError):
        parse_response(200, {}, json.dumps([1, 2, 3]))


def test_parse_response_2xx_empty_body_raises():
    with pytest.raises(BrontoAPIError):
        parse_response(204, {}, "")


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (401, BrontoAuthenticationError),
        (404, BrontoNotFoundError),
        (429, BrontoRateLimitError),
        (500, BrontoServerError),
    ],
)
def test_parse_response_maps_error_status_to_class(status, cls):
    body = json.dumps({"details": "boom"})
    with pytest.raises(cls) as excinfo:
        parse_response(status, {}, body)
    assert excinfo.value.status_code == status


def test_parse_response_non_json_error_body_does_not_mask_status():
    with pytest.raises(BrontoNotFoundError) as excinfo:
        parse_response(404, {}, "<html>not found</html>")
    assert excinfo.value.status_code == 404
