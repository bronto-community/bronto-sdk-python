"""Tests for client.search — the typed POST /search surface."""

import json

import pytest
from pydantic import ValidationError

from bronto_sdk.models import SearchRequest
from tests.conftest import BASE_URL, ClientHarness, RequestRecorder, make_transport

SEARCH_BODY = {
    "events": [
        {
            "@raw": "boom",
            "@timestamp": 1709251200000,
            "message_kvs": {"level": "ERROR"},
            "attributes": {"$service.name": "checkout"},
            "metadata": {"sequence": 9007199254740993},
        }
    ],
    "groups_series": [{"name": "checkout", "count": 12, "timeseries": [{"count": 12}]}],
    "metadata": {"correlation_id": "cid-9"},
    "is_exact": True,
}


def test_run_posts_to_search_with_the_model_payload(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    request = SearchRequest(
        select=["count(*)"], from_=["ds-1"], where="level = 'ERROR'"
    )
    parity.call(client.search.run(request))
    assert len(recorder.requests) == 1
    assert recorder.last.method == "POST"
    assert str(recorder.last.url) == f"{BASE_URL}/search"
    assert json.loads(recorder.last.read()) == {
        "select": ["count(*)"],
        "from": ["ds-1"],
        "where": "level = 'ERROR'",
    }
    parity.close(client)


def test_run_accepts_a_dict_and_sends_the_same_body(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.search.run(SearchRequest(select=["*"], from_expr="c = 'p'")))
    parity.call(client.search.run({"select": ["*"], "from_expr": "c = 'p'"}))
    assert recorder.requests[0].read() == recorder.requests[1].read()
    assert json.loads(recorder.last.read()) == {"select": ["*"], "from_expr": "c = 'p'"}
    parity.close(client)


def test_run_accepts_the_wire_spelling_of_from(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.search.run({"select": ["*"], "from": ["ds-1"]}))
    assert json.loads(recorder.last.read()) == {"select": ["*"], "from": ["ds-1"]}
    parity.close(client)


def test_run_rejects_an_invalid_dict_before_any_request(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(ValidationError):
        parity.call(
            client.search.run({"select": ["*"], "from": ["a"], "from_expr": "b"})
        )
    assert recorder.requests == []
    parity.close(client)


def test_run_parses_the_response_into_a_model(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.search.run(SearchRequest(select=["*"])))
    assert response.is_exact is True
    assert response.metadata is not None
    assert response.metadata.correlation_id == "cid-9"
    assert response.events is not None
    assert response.events[0].raw == "boom"
    assert response.events[0].message_kvs == {"level": "ERROR"}
    assert response.groups_series is not None
    assert response.groups_series[0].count == 12
    parity.close(client)


def test_run_preserves_a_js_unsafe_sequence_number(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.search.run(SearchRequest(select=["*"])))
    assert response.events is not None
    metadata = response.events[0].metadata
    assert metadata is not None
    assert metadata.sequence == 9007199254740993
    parity.close(client)


def test_run_passes_per_request_options_through(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=SEARCH_BODY)
    client = parity.build(transport, base_url=BASE_URL)
    parity.call(
        client.search.run(SearchRequest(select=["*"]), options={"api_key": "tenant-a"})
    )
    assert recorder.last.headers["x-bronto-api-key"] == "tenant-a"
    parity.close(client)
