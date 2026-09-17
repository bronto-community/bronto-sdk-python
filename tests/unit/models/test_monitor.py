"""Tests for the monitor models."""

import pytest
from pydantic import ValidationError

from bronto_sdk.models import Monitor, MonitorEventsResponse

PATTERN_MONITOR = {
    "id": "b415076f-692e-4683-ae7e-28bb73ebf454",
    "name": "Your worst nightmare",
    "description": "A box went bye-bye",
    "metric_id": "7559517c-6137-4cb3-a787-951f7e9c146d",
    "monitor_type": "PATTERN",
    "threshold": 1.0,
    "comparison_operator": "ABOVE_OR_EQUAL",
    "no_data_status": "OK",
    "window": "last 30 minutes",
    "actions": [{"type": "EMAIL", "email": "someone@example.com"}],
    "notify_once": False,
    "ai_report_enabled": False,
    "status": "OK",
    "last_trigger_ts": 1755364510857,
    "monitored_groups": [],
    "group_retention": 0,
    "metadata": {"created_at": 1738857414077},
    "aux": {"query_mode": "raw"},
    "tags": {},
    "queries": [
        {
            "id": "498dacb9-5791-84bd-5231-043ba801a965",
            "select": ["COUNT(*)"],
            "from": ["078a81b8-9d25-2046-7719-8121cc888e1f"],
            "where": "'hell_on_earth'",
        }
    ],
    "formulas": [],
}

CHANGE_DETECTION_MONITOR = {
    "id": "8eb8ff86-8707-41bb-a50b-a43b6d32c53b",
    "name": "Drop In Dopamine",
    "monitor_type": "CHANGE_DETECTION",
    "threshold": -30.0,
    "comparison_operator": "BELOW",
    "window": "Last 1 hours",
    "compare_to": "2 hours ago",
    "change_type": "PERCENTAGE",
    "status": "OK",
    "ai_report_enabled": False,
    "ai_report_instructions": "Check the patient's vitals.",
    "metadata": {"created_at": 1766089704465, "modified_at": 1770887696875},
}


@pytest.mark.parametrize("payload", [PATTERN_MONITOR, CHANGE_DETECTION_MONITOR])
def test_real_monitors_round_trip_without_loss(payload):
    assert (
        Monitor.model_validate(payload).model_dump(by_alias=True, exclude_none=True)
        == payload
    )


def test_the_playbook_field_reads_through():
    monitor = Monitor.model_validate(CHANGE_DETECTION_MONITOR)
    assert monitor.ai_report_instructions == "Check the patient's vitals."


def test_change_detection_fields_are_typed_not_buried_in_extras():
    monitor = Monitor.model_validate(CHANGE_DETECTION_MONITOR)
    assert monitor.compare_to == "2 hours ago"
    assert monitor.change_type == "PERCENTAGE"
    assert monitor.model_extra == {}


def test_queries_are_typed_and_keep_the_from_wire_key():
    monitor = Monitor.model_validate(PATTERN_MONITOR)
    assert monitor.queries is not None
    query = monitor.queries[0]
    assert query.from_ == ["078a81b8-9d25-2046-7719-8121cc888e1f"]
    assert query.select == ["COUNT(*)"]
    assert "from" in monitor.model_dump(by_alias=True, exclude_none=True)["queries"][0]


def test_aggregation_parses_into_a_model():
    monitor = Monitor.model_validate(
        {
            "id": "m-1",
            "name": "n",
            "queries": [{"aggregation": [{"time": "count", "reduce_to": "avg"}]}],
        }
    )
    assert monitor.queries is not None
    aggregation = monitor.queries[0].aggregation
    assert aggregation is not None
    assert aggregation[0].reduce_to == "avg"


def test_a_monitor_carrying_only_its_identity_still_parses():
    monitor = Monitor.model_validate({"id": "m-1", "name": "n"})
    assert monitor.status is None
    assert monitor.ai_report_enabled is None
    assert monitor.actions is None


def test_a_monitor_without_an_identity_is_rejected():
    with pytest.raises(ValidationError) as caught:
        Monitor.model_validate({"name": "n"})
    assert {"id"} == {error["loc"][0] for error in caught.value.errors()}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "DEGRADED"),
        ("monitor_type", "FORECAST"),
        ("comparison_operator", "SIDEWAYS"),
    ],
)
def test_an_unknown_enum_value_widens_the_vocabulary_rather_than_raising(field, value):
    monitor = Monitor.model_validate({"id": "m-1", "name": "n", field: value})
    assert getattr(monitor, field) == value


def test_events_response_reads_the_monitor_events_key():
    payload = {
        "monitor_events": [
            {
                "monitor_id": "m-1",
                "previous_status": "OK",
                "monitor_status": "ALERT",
                "time": 1700000000000,
                "message": "The monitor changed status: OK --> ALERT.",
            }
        ],
        "groups_history": [
            {
                "group_id": "host:a",
                "history": [{"status": "ALERT", "time": 1700000000000}],
            }
        ],
    }
    response = MonitorEventsResponse.model_validate(payload)
    assert response.monitor_events is not None
    assert response.groups_history is not None
    assert response.monitor_events[0].monitor_status == "ALERT"
    assert isinstance(response.monitor_events[0].time, int)
    history = response.groups_history[0].history
    assert history is not None
    assert history[0].time == 1700000000000
    assert response.model_dump(by_alias=True, exclude_none=True) == payload


def test_the_events_key_is_not_a_synonym_for_monitor_events():
    response = MonitorEventsResponse.model_validate({"events": [{"time": 1}]})
    assert response.monitor_events is None
    assert response.model_extra == {"events": [{"time": 1}]}


def test_an_empty_events_response_parses():
    response = MonitorEventsResponse.model_validate(
        {"monitor_events": [], "groups_history": []}
    )
    assert response.monitor_events == []
