"""Tests for the error hierarchy, envelope parsing, and redaction."""

import pytest

from bronto_sdk import (
    BrontoAPIError,
    BrontoAuthenticationError,
    BrontoBadRequestError,
    BrontoError,
    BrontoNotFoundError,
    BrontoPermissionError,
    BrontoRateLimitError,
    BrontoServerError,
)
from bronto_sdk._errors import error_from_response


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, BrontoBadRequestError),
        (401, BrontoAuthenticationError),
        (403, BrontoPermissionError),
        (404, BrontoNotFoundError),
        (429, BrontoRateLimitError),
        (500, BrontoServerError),
        (502, BrontoServerError),
        (503, BrontoServerError),
        (504, BrontoServerError),
        (599, BrontoServerError),
    ],
)
def test_status_maps_to_subclass(status, expected):
    err = error_from_response(status, {}, None)
    assert type(err) is expected
    assert isinstance(err, BrontoAPIError)
    assert isinstance(err, BrontoError)
    assert err.status_code == status


def test_unmapped_status_falls_back_to_base_api_error():
    # 418 is neither in the exact map nor a 5xx: exact-type base class.
    err = error_from_response(418, {}, None)
    assert type(err) is BrontoAPIError
    assert err.status_code == 418


def test_envelope_is_parsed_when_present():
    body = (
        '{"code": 404, "type": "Not Found", '
        '"correlation_id": "abc123", "details": "Monitor not found"}'
    )
    err = error_from_response(404, {}, body)
    assert isinstance(err, BrontoNotFoundError)
    assert err.correlation_id == "abc123"
    assert err.details == "Monitor not found"
    assert err.error_type == "Not Found"
    assert "Monitor not found" in str(err)


def test_message_prefers_details_then_message_then_body():
    from_details = error_from_response(400, {}, '{"details": "d", "message": "m"}')
    assert from_details.details == "d"
    assert "d" in str(from_details)

    from_message = error_from_response(400, {}, '{"message": "m"}')
    assert from_message.details is None
    assert "m" in str(from_message)

    from_body = error_from_response(400, {}, "raw plain text failure")
    assert "raw plain text failure" in str(from_body)


def test_malformed_and_absent_envelopes_degrade_gracefully():
    # Non-JSON body: no envelope fields, raw body becomes the message snippet.
    err = error_from_response(400, {}, "<html>not json</html>")
    assert err.correlation_id is None
    assert err.details is None
    assert err.error_type is None
    assert "<html>not json</html>" in str(err)

    # JSON that is not an object (a list) is ignored as an envelope.
    list_err = error_from_response(400, {}, "[1, 2, 3]")
    assert list_err.details is None

    # Empty body: a generic message, still valid.
    empty = error_from_response(500, {}, None)
    assert str(empty)  # non-empty
    assert empty.correlation_id is None


@pytest.mark.parametrize(
    ("status", "retryable"),
    [
        (400, False),
        (401, False),
        (403, False),
        (404, False),
        (429, True),
        (500, True),
        (503, True),
        (599, True),
    ],
)
def test_retryable_flag(status, retryable):
    assert error_from_response(status, {}, None).retryable is retryable


def test_rate_limit_headers_parsed():
    headers = {"Retry-After": "30", "RateLimit-Reset": "1700000000"}
    err = error_from_response(429, headers, None)
    assert isinstance(err, BrontoRateLimitError)
    assert err.retry_after == 30
    assert err.rate_limit_reset == 1700000000


def test_rate_limit_headers_absent_by_default():
    err = error_from_response(429, {}, None)
    assert isinstance(err, BrontoRateLimitError)
    assert err.retry_after is None
    assert err.rate_limit_reset is None


def test_rate_limit_headers_invalid_values_are_none():
    headers = {"Retry-After": "soon", "RateLimit-Reset": ""}
    err = error_from_response(429, headers, None)
    assert isinstance(err, BrontoRateLimitError)
    assert err.retry_after is None
    assert err.rate_limit_reset is None


def test_rate_limit_headers_absent_among_other_headers():
    err = error_from_response(429, {"X-Request-Id": "r-1"}, None)
    assert isinstance(err, BrontoRateLimitError)
    assert err.retry_after is None
    assert err.rate_limit_reset is None


def test_str_surfaces_status_and_correlation_id():
    err = error_from_response(
        404, {}, '{"correlation_id": "cid-42", "details": "gone"}'
    )
    rendered = str(err)
    assert "HTTP 404" in rendered
    assert "cid-42" in rendered


def test_str_omits_correlation_id_when_absent():
    err = error_from_response(500, {}, None)
    assert "correlation_id" not in str(err)
    assert "HTTP 500" in str(err)


@pytest.mark.parametrize(
    "header_name",
    ["Authorization", "X-BRONTO-API-KEY", "x-bronto-api-key", "api_key", "token"],
)
def test_credentials_are_redacted_in_headers(header_name):
    secret = "super-secret-value"
    err = error_from_response(500, {header_name: secret}, None)
    assert err.headers[header_name] == "[redacted]"
    assert secret not in str(err)
    assert secret not in repr(err)
    assert secret not in "".join(str(v) for v in err.headers.values())


def test_non_sensitive_headers_are_preserved():
    err = error_from_response(500, {"X-Request-Id": "keep-me"}, None)
    assert err.headers["X-Request-Id"] == "keep-me"


def test_body_is_stored_verbatim():
    err = error_from_response(500, {}, "body")
    assert err.body == "body"
