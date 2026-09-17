"""Sync/async parity tests: both clients must behave identically."""

import json

import httpx
import pytest

import bronto_sdk
from bronto_sdk import (
    BrontoAuthenticationError,
    BrontoConfigError,
    BrontoConnectionError,
    BrontoNotFoundError,
)
from tests.conftest import BASE_URL, ClientHarness, RequestRecorder, make_transport


def test_get_joins_url_for_both_path_styles(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body={"ok": True})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.get(client, "/search")
    parity.get(client, "monitors/m-1")
    assert str(recorder.requests[0].url) == f"{BASE_URL}/search"
    assert str(recorder.requests[1].url) == f"{BASE_URL}/monitors/m-1"
    parity.close(client)


def test_get_returns_parsed_json_object(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, json_body={"count": 3, "events": []})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    assert parity.get(client, "/search") == {"count": 3, "events": []}
    parity.close(client)


def test_api_key_header_wired(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="secret-key", base_url=BASE_URL)
    parity.get(client, "/search")
    assert recorder.last.headers["X-BRONTO-API-KEY"] == "secret-key"
    assert "authorization" not in recorder.last.headers
    parity.close(client)


def test_bearer_header_wired(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = parity.build(transport, bearer_token="jwt", base_url=BASE_URL)
    parity.get(client, "/search")
    assert recorder.last.headers["authorization"] == "jwt"
    assert "x-bronto-api-key" not in recorder.last.headers
    parity.close(client)


def test_user_agent_header(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.get(client, "/search")
    assert (
        recorder.last.headers["user-agent"] == f"bronto-sdk-python/{bronto_sdk.VERSION}"
    )
    parity.close(client)


def test_custom_header_via_options_is_sent(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.get(client, "/search", options={"headers": {"X-BRONTO-SOURCE": "svc"}})
    assert recorder.last.headers["x-bronto-source"] == "svc"
    parity.close(client)


def test_get_sends_query_params(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.get(client, "/datasets", params={"from_expr": "logs"})
    assert recorder.last.url.params["from_expr"] == "logs"
    parity.close(client)


def test_post_sends_json_body(parity: ClientHarness, recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    parity.post(client, "/search", json={"select": ["a"]})
    assert json.loads(recorder.last.read()) == {"select": ["a"]}
    parity.close(client)


def test_error_status_maps_to_subclass(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(
        recorder,
        status_code=404,
        json_body={"details": "gone", "correlation_id": "cid-1"},
    )
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(BrontoNotFoundError) as excinfo:
        parity.get(client, "/monitors/x")
    assert excinfo.value.status_code == 404
    assert excinfo.value.correlation_id == "cid-1"
    parity.close(client)


def test_per_request_credential_on_credentialless_client(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder)
    client = parity.build(transport, base_url=BASE_URL)
    parity.get(client, "/search", options={"api_key": "req-key"})
    assert recorder.last.headers["x-bronto-api-key"] == "req-key"
    parity.close(client)


def test_multitenant_no_credential_leak_between_calls(
    parity: ClientHarness, recorder: RequestRecorder
):
    # One credential-less client, two calls with different credentials: each
    # request must carry only its own, and nothing must persist between them.
    transport = make_transport(recorder)
    client = parity.build(transport, base_url=BASE_URL)
    parity.get(client, "/search", options={"api_key": "tenant-a"})
    parity.get(client, "/search", options={"bearer_token": "tenant-b"})
    assert recorder.requests[0].headers["x-bronto-api-key"] == "tenant-a"
    assert "authorization" not in recorder.requests[0].headers
    assert recorder.requests[1].headers["authorization"] == "tenant-b"
    assert "x-bronto-api-key" not in recorder.requests[1].headers
    parity.close(client)


def test_credentialless_client_requires_a_credential(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder)
    client = parity.build(transport, base_url=BASE_URL)
    with pytest.raises(BrontoConfigError):
        parity.get(client, "/search")
    parity.close(client)


def test_bound_client_rejects_per_request_credential(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder)
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(BrontoConfigError):
        parity.get(client, "/search", options={"api_key": "other"})
    parity.close(client)


def test_transport_failure_wrapped_without_leaking_credential(parity: ClientHarness):
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failure")

    transport = httpx.MockTransport(boom)
    client = parity.build(transport, api_key="super-secret", base_url=BASE_URL)
    with pytest.raises(BrontoConnectionError) as excinfo:
        parity.get(client, "/search")
    assert "super-secret" not in str(excinfo.value)
    assert "super-secret" not in repr(excinfo.value)
    parity.close(client)


def test_authentication_error_is_brontoapierror(
    parity: ClientHarness, recorder: RequestRecorder
):
    transport = make_transport(recorder, status_code=401, json_body={"details": "nope"})
    client = parity.build(transport, api_key="k", base_url=BASE_URL)
    with pytest.raises(BrontoAuthenticationError):
        parity.get(client, "/search")
    parity.close(client)
