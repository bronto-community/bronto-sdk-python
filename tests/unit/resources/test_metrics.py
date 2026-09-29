"""Tests for client.metrics — GET /metrics/definitions/{id}."""

import pytest

from bronto_sdk import BrontoNotFoundError
from tests.conftest import BASE_URL, ClientHarness, RequestRecorder, make_transport

DEFINITION_BODY = {
    "id": "md-1",
    "queries": [
        {
            "name": "oom",
            "select": ["COUNT(*)"],
            "from": ["078a81b8"],
            "from_expr": "",
            "where": "'oom-kill'",
            "groups": ["host"],
        }
    ],
    "formulas": [{"name": "f", "expression": "a / b"}],
    "source_type": "LOG_BASED_METRIC",
}


def test_retrieve_definition_gets_one_definition(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DEFINITION_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.metrics.retrieve_definition("md-1"))
    assert recorder.last.method == "GET"
    assert str(recorder.last.url) == f"{BASE_URL}/metrics/definitions/md-1"
    parity.close(client)


def test_retrieve_definition_parses_the_queries(
    parity: ClientHarness, recorder: RequestRecorder
):
    """The queries are what a caller comes here for, `from` alias and all."""
    transport = make_transport(recorder, json_body=DEFINITION_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    definition = parity.call(client.metrics.retrieve_definition("md-1"))
    assert definition.id == "md-1"
    assert definition.queries is not None
    query = definition.queries[0]
    assert query.from_ == ["078a81b8"]
    assert query.where == "'oom-kill'"
    assert query.groups == ["host"]
    assert definition.formulas is not None
    assert definition.formulas[0].expression == "a / b"
    # Unknown fields ride along rather than being dropped.
    assert definition.model_extra == {"source_type": "LOG_BASED_METRIC"}
    parity.close(client)


def test_retrieve_definition_quotes_the_id_into_one_segment(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DEFINITION_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.metrics.retrieve_definition("metric/1"))
    assert str(recorder.last.url) == f"{BASE_URL}/metrics/definitions/metric%2F1"
    parity.close(client)


def test_retrieve_definition_rejects_an_empty_id(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DEFINITION_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(ValueError, match="metric_id must be a non-empty string"):
        parity.call(client.metrics.retrieve_definition(""))
    assert recorder.requests == []
    parity.close(client)


def test_retrieve_definition_surfaces_a_404_as_a_typed_error(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(
        recorder,
        status_code=404,
        json_body={"details": "no such definition", "correlation_id": "cid-4"},
    )
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(BrontoNotFoundError) as excinfo:
        parity.call(client.metrics.retrieve_definition("md-1"))
    assert excinfo.value.status_code == 404
    assert excinfo.value.correlation_id == "cid-4"
    parity.close(client)
