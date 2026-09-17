"""Tests for client.datasets — the typed GET /datasets surface."""

import pytest

from tests.conftest import BASE_URL, ClientHarness, RequestRecorder, make_transport

DATASETS_BODY = {
    "datasets": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "collection": "demo",
            "dataset": "firewall",
            "is_system_generated": False,
        }
    ]
}


def test_list_without_a_selector_sends_no_query_string(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DATASETS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.datasets.list())
    assert len(recorder.requests) == 1
    assert recorder.last.method == "GET"
    assert str(recorder.last.url) == f"{BASE_URL}/datasets"
    parity.close(client)


def test_list_sends_ids_as_repeated_from_keys(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DATASETS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.datasets.list(from_=["ds-a", "ds-b"]))
    assert recorder.last.url.params.get_list("from") == ["ds-a", "ds-b"]
    assert str(recorder.last.url) == f"{BASE_URL}/datasets?from=ds-a&from=ds-b"
    parity.close(client)


def test_list_sends_only_the_expression_when_given_one(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DATASETS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.call(client.datasets.list(from_expr="collection = 'prod'"))
    assert dict(recorder.last.url.params) == {"from_expr": "collection = 'prod'"}
    parity.close(client)


def test_list_rejects_both_selectors_before_any_request(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body=DATASETS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(ValueError):
        parity.call(client.datasets.list(from_=["ds-a"], from_expr="c = 'p'"))
    assert recorder.requests == []
    parity.close(client)


def test_list_parses_the_datasets(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder, json_body=DATASETS_BODY)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    response = parity.call(client.datasets.list())
    assert response.datasets is not None
    assert response.datasets[0].collection == "demo"
    assert response.datasets[0].dataset == "firewall"
    parity.close(client)


def test_list_distinguishes_absent_from_empty(
    parity: ClientHarness, recorder: RequestRecorder
):
    # A selector matching nothing returns 200 with an empty array, which is a
    # different answer from the key being absent entirely.
    transport = make_transport(recorder, json_body={"datasets": []})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    assert parity.call(client.datasets.list()).datasets == []
    parity.close(client)

    empty = make_transport(recorder, json_body={})
    client = parity.build(empty, api_key="k", base_url=BASE_URL)
    assert parity.call(client.datasets.list()).datasets is None
    parity.close(client)
