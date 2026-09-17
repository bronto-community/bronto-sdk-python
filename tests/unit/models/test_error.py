"""Tests for the error envelope model."""

import json

import pytest

from bronto_sdk._errors import error_from_response
from bronto_sdk.models import ErrorResponse

EXAMPLES = [
    {
        "code": 400,
        "type": "Bad Request",
        "correlation_id": "95c6a974e3ab01209b6b0dfedb1b16c5",
        "details": "Validation failed: 'name' field is required and cannot be empty",
    },
    {
        "code": 400,
        "type": "Bad Request",
        "correlation_id": "00d8a51bb2874f2583670317a4fb8db7",
        "details": "Invalid metric_type 'INVALID'. Must be one of: COUNTER, GAUGE",
    },
    {
        "code": 403,
        "type": "Forbidden",
        "correlation_id": "40276639de0f49d586e32edd8c4f6b34",
        "details": "Access denied. User does not have permission",
    },
    {
        "code": 404,
        "type": "Not Found",
        "correlation_id": "605f832bcfe44a1081441691c8d42253",
        "details": "Metric definition template not found",
    },
    {
        "code": 429,
        "type": "Too Many Requests",
        "correlation_id": "53909ed43c544531b7a555e295960437",
        "details": "Rate limit exceeded. Maximum 100 requests within a 5-minute window",
    },
    {
        "code": 500,
        "type": "Internal Server Error",
        "correlation_id": "b129b8e0e66c41aa9541a30f67e38ce2",
        "details": "An unexpected error occurred while processing your request",
    },
]

PARTIAL_ENVELOPES = [{"code": 404}, {"details": "boom"}, {}]


@pytest.mark.parametrize("payload", EXAMPLES)
def test_spec_examples_parse_field_for_field(payload):
    model = ErrorResponse.model_validate(payload)
    assert model.code == payload["code"]
    assert model.type == payload["type"]
    assert model.correlation_id == payload["correlation_id"]
    assert model.details == payload["details"]


@pytest.mark.parametrize("payload", [*EXAMPLES, *PARTIAL_ENVELOPES])
def test_model_and_hand_rolled_parser_never_disagree(payload):
    # The drift guard. `_errors.py` stays pydantic-free so that building an
    # exception can never itself raise; this asserts the two readings of the
    # same envelope stay identical anyway.
    error = error_from_response(payload.get("code", 500), {}, json.dumps(payload))
    model = ErrorResponse.model_validate(payload)
    assert model.correlation_id == error.correlation_id
    assert model.details == error.details
    assert model.type == error.error_type


@pytest.mark.parametrize("payload", PARTIAL_ENVELOPES)
def test_partial_envelopes_parse_instead_of_raising(payload):
    model = ErrorResponse.model_validate(payload)
    for field, value in payload.items():
        assert getattr(model, field) == value


def test_unknown_envelope_field_survives_a_round_trip():
    payload = {"code": 400, "type": "Bad Request", "hint": "try again"}
    model = ErrorResponse.model_validate(payload)
    assert model.model_extra == {"hint": "try again"}
    assert model.model_dump(exclude_none=True) == payload
