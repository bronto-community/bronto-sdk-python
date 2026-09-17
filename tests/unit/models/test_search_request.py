"""Tests for the search request model."""

import pytest
from pydantic import ValidationError

from bronto_sdk.models import SearchRequest

SPEC_REQUEST_EXAMPLES = [
    {
        "from": ["550e8400-e29b-41d4-a716-446655440000"],
        "time_range": "Last 1 hour",
        "where": "level = 'error'",
        "select": ["message", "timestamp", "source"],
        "limit": 100,
        "most_recent_first": True,
    },
    {
        "from_expr": "environment = 'production'",
        "time_range": "Last 24 hours",
        "where": "status >= 400",
        "select": ["count(*)"],
        "groups": ["service", "region"],
        "num_of_slices": 24,
    },
    {
        "from": ["297bb888-83b1-44e0-8ab6-47879f1275a2"],
        "time_range": "Last 6 hours",
        "select": ["avg(response_time_ms)", "max(response_time_ms)", "count(*)"],
        "num_of_slices": 72,
        "async_enabled": True,
    },
]

AUDIT_TIMESERIES_BODY = {
    "async_enabled": False,
    "from": [".audit-trail.events"],
    "groups": ['"service_payload.monitor_name"'],
    "num_of_slices": 20,
    "limit": 10,
    "select": ["count(*)"],
    "from_ts": 1784851200000,
    "to_ts": 1784937600000,
    "where": "\"event_info.type\"='MONITOR_STATE_CHANGE'",
}

AUDIT_EVENTS_BODY = {
    "async_enabled": False,
    "from": [".audit-trail.events"],
    "select": ["*"],
    "most_recent_first": True,
    "from_ts": 1784851200000,
    "to_ts": 1784937600000,
    "where": "\"event_info.type\"='MONITOR_STATE_CHANGE'",
    "limit": 50,
}

MCP_VALIDATION_PROBE = {
    "select": ["count(*)"],
    "time_range": "Last 24 hours",
    "num_of_slices": 1,
}


def test_to_payload_emits_the_wire_key_not_the_python_name():
    payload = SearchRequest(
        select=["count(*)"], from_=[".audit-trail.events"]
    ).to_payload()
    assert payload == {"select": ["count(*)"], "from": [".audit-trail.events"]}
    assert "from_" not in payload


def test_to_payload_omits_every_unset_field():
    # Unset fields must not be sent, so the server applies its own defaults.
    # Baking the spec's `limit: 100` into the model would change the body of
    # every request that never asked for a limit.
    assert SearchRequest(select=["*"]).to_payload() == {"select": ["*"]}


@pytest.mark.parametrize(
    "body",
    [*SPEC_REQUEST_EXAMPLES, AUDIT_TIMESERIES_BODY, AUDIT_EVENTS_BODY],
)
def test_real_bodies_round_trip_unchanged(body):
    assert SearchRequest.model_validate(body).to_payload() == body


def test_a_request_with_no_dataset_selector_is_accepted():
    assert SearchRequest.model_validate(MCP_VALIDATION_PROBE).to_payload() == (
        MCP_VALIDATION_PROBE
    )


@pytest.mark.parametrize(
    ("body", "expected_type"),
    [
        ({}, "missing"),
        ({"select": []}, "too_short"),
        (
            {"select": ["*"], "from": ["a"], "from_expr": "b"},
            "value_error",
        ),
        (
            {"select": ["*"], "time_range": "Last 1 hour", "from_ts": 1, "to_ts": 2},
            "value_error",
        ),
        ({"select": ["*"], "from_ts": 1}, "value_error"),
        ({"select": ["*"], "to_ts": 2}, "value_error"),
        ({"select": ["*"], "limit": 0}, "greater_than_equal"),
        ({"select": ["*"], "limit": 10001}, "less_than_equal"),
        ({"select": ["*"], "per_page": 0}, "greater_than_equal"),
    ],
)
def test_illegal_requests_are_rejected_before_the_call(body, expected_type):
    with pytest.raises(ValidationError) as caught:
        SearchRequest.model_validate(body)
    assert expected_type in {error["type"] for error in caught.value.errors()}


def test_an_unmodelled_parameter_is_forwarded_rather_than_dropped():
    # The same escape hatch `client.post` provides: a /search parameter this
    # SDK version does not know about must still reach the API.
    payload = SearchRequest.model_validate(
        {"select": ["*"], "future_param": "value"}
    ).to_payload()
    assert payload["future_param"] == "value"


def test_construction_by_field_name_and_by_wire_alias_agree():
    by_name = SearchRequest(select=["*"], from_=["a"])
    by_alias = SearchRequest.model_validate({"select": ["*"], "from": ["a"]})
    assert by_name.to_payload() == by_alias.to_payload()
