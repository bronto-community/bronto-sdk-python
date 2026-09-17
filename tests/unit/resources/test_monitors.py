"""Tests for client.monitors — GET /monitors/{id} and its event history."""

import pytest

from bronto_sdk import BrontoNotFoundError
from tests.conftest import BASE_URL, ClientHarness, RequestRecorder, make_transport

MONITOR_BODY = {
    "id": "41521f35-1b06-41f0-9cdc-9a938b5739d1",
    "name": "checkout errors",
    "threshold": 5.0,
    "ai_report_instructions": "check the deploy log first",
    "last_trigger_ts": 1711390455601,
}

EVENTS_BODY = {
    "monitor_events": [
        {
            "monitor_id": "m-1",
            "time": 1711390455601,
            "monitor_status": "ALERT",
            "previous_status": "OK",
            "message": "threshold breached",
        }
    ],
    "groups_history": [
        {"monitor_id": "m-1", "group_id": "g-1", "history": [{"status": "ALERT"}]}
    ],
}


MONITORS_BODY = {"monitors": [MONITOR_BODY, {"id": "m-2", "name": "latency"}]}


def test_list_gets_the_monitors_collection(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=MONITORS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.monitors.list())
    assert len(recorder.requests) == 1
    assert recorder.last.method == "GET"
    # The endpoint takes no filters, so there must be no query string at all.
    assert str(recorder.last.url) == f"{BASE_URL}/monitors"
    parity.close(client)


def test_list_parses_every_monitor(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder, json_body=MONITORS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.monitors.list())
    assert response.monitors is not None
    assert [m.name for m in response.monitors] == ["checkout errors", "latency"]
    assert response.monitors[0].ai_report_instructions == "check the deploy log first"
    parity.close(client)


def test_list_distinguishes_absent_from_empty(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body={"monitors": []})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    assert parity.call(client.monitors.list()).monitors == []
    parity.close(client)

    empty = make_transport(recorder, json_body={})
    client = parity.build(empty, api_key="k", base_url=BASE_URL)
    assert parity.call(client.monitors.list()).monitors is None
    parity.close(client)


def test_list_passes_per_request_options_through(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=MONITORS_BODY)
    client = parity.build(transport, base_url=BASE_URL)
    parity.call(client.monitors.list(options={"api_key": "tenant-a"}))
    assert recorder.last.headers["x-bronto-api-key"] == "tenant-a"
    parity.close(client)


def test_retrieve_gets_the_monitor_path(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=MONITOR_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.monitors.retrieve("m-1"))
    assert len(recorder.requests) == 1
    assert recorder.last.method == "GET"
    assert str(recorder.last.url) == f"{BASE_URL}/monitors/m-1"
    parity.close(client)


def test_retrieve_quotes_the_monitor_id_into_one_segment(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=MONITOR_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.monitors.retrieve("monitor/1"))
    assert str(recorder.last.url) == f"{BASE_URL}/monitors/monitor%2F1"
    parity.close(client)


def test_retrieve_rejects_an_empty_monitor_id(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=MONITOR_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(ValueError):
        parity.call(client.monitors.retrieve(""))
    assert recorder.requests == []
    parity.close(client)


def test_retrieve_parses_the_monitor(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder, json_body=MONITOR_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    monitor = parity.call(client.monitors.retrieve("m-1"))
    assert monitor.name == "checkout errors"
    assert monitor.ai_report_instructions == "check the deploy log first"
    assert monitor.last_trigger_ts == 1711390455601
    parity.close(client)


def test_retrieve_surfaces_a_404_as_a_typed_error(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(
        recorder,
        status_code=404,
        json_body={"details": "no such monitor", "correlation_id": "cid-4"},
    )
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(BrontoNotFoundError) as excinfo:
        parity.call(client.monitors.retrieve("m-1"))
    assert excinfo.value.status_code == 404
    assert excinfo.value.correlation_id == "cid-4"
    parity.close(client)


def test_events_without_bounds_sends_no_query_string(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=EVENTS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.monitors.events("m-1"))
    assert str(recorder.last.url) == f"{BASE_URL}/monitors/m-1/events"
    parity.close(client)


def test_events_sends_only_the_bounds_that_were_given(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=EVENTS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.monitors.events("m-1", from_ts=1709251200000))
    assert dict(recorder.last.url.params) == {"from_ts": "1709251200000"}
    parity.call(client.monitors.events("m-1", to_ts=1711390455601))
    assert dict(recorder.last.url.params) == {"to_ts": "1711390455601"}
    parity.call(
        client.monitors.events("m-1", from_ts=1709251200000, to_ts=1711390455601)
    )
    assert dict(recorder.last.url.params) == {
        "from_ts": "1709251200000",
        "to_ts": "1711390455601",
    }
    parity.close(client)


def test_events_rejects_an_empty_monitor_id(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=EVENTS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(ValueError):
        parity.call(client.monitors.events(""))
    assert recorder.requests == []
    parity.close(client)


def test_events_parses_the_monitor_events_array(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=EVENTS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.monitors.events("m-1"))
    assert response.monitor_events is not None
    assert response.monitor_events[0].monitor_status == "ALERT"
    assert response.monitor_events[0].time == 1711390455601
    assert response.groups_history is not None
    assert response.groups_history[0].group_id == "g-1"
    parity.close(client)


def test_events_key_is_not_a_synonym_for_monitor_events(
    parity: ClientHarness, recorder: RequestRecorder
):
    # The endpoint keys its array `monitor_events`. A payload keyed `events`
    # validates silently and yields nothing, so pin the trap rather than let a
    # future refactor "fix" the field name.
    transport = make_transport(recorder, json_body={"events": [{"monitor_id": "m-1"}]})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.monitors.events("m-1"))
    assert response.monitor_events is None
    parity.close(client)
