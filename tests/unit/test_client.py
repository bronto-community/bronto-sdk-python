"""Tests specific to the synchronous BrontoClient."""

import httpx
import pytest

from bronto_sdk import BrontoAPIError, BrontoClient, BrontoConfigError
from tests.conftest import BASE_URL, RequestRecorder, make_transport


def test_base_url_overrides_region(recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = BrontoClient(
        api_key="k",
        region="eu",
        base_url="https://custom.example.com",
        http_client=httpx.Client(transport=transport),
    )
    client.get("/search")
    assert str(recorder.last.url).startswith("https://custom.example.com/")
    client.close()


def test_region_resolves_rest_base_url(recorder: RequestRecorder):
    transport = make_transport(recorder)
    client = BrontoClient(
        api_key="k", region="eu", http_client=httpx.Client(transport=transport)
    )
    client.get("/search")
    assert str(recorder.last.url) == "https://api.eu.bronto.io/search"
    client.close()


def test_missing_endpoint_raises():
    with pytest.raises(BrontoConfigError):
        BrontoClient(api_key="k")


def test_invalid_region_raises():
    with pytest.raises(BrontoConfigError):
        BrontoClient(api_key="k", region="evil.com/")


def test_from_env_reads_region(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BRONTO_API_KEY", "env-key")
    monkeypatch.setenv("BRONTO_REGION", "us")
    monkeypatch.delenv("BRONTO_BASE_URL", raising=False)
    client = BrontoClient.from_env()
    assert client._base_url == "https://api.us.bronto.io"
    client.close()


def test_from_env_base_url_wins_over_region(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BRONTO_API_KEY", "env-key")
    monkeypatch.setenv("BRONTO_REGION", "us")
    monkeypatch.setenv("BRONTO_BASE_URL", "https://staging.example.com")
    client = BrontoClient.from_env()
    assert client._base_url == "https://staging.example.com"
    client.close()


def test_from_env_missing_api_key_names_it(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BRONTO_API_KEY", raising=False)
    monkeypatch.setenv("BRONTO_REGION", "us")
    with pytest.raises(BrontoConfigError) as excinfo:
        BrontoClient.from_env()
    assert "BRONTO_API_KEY" in str(excinfo.value)


def test_from_env_missing_region_names_it(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BRONTO_API_KEY", "env-key")
    monkeypatch.delenv("BRONTO_REGION", raising=False)
    monkeypatch.delenv("BRONTO_BASE_URL", raising=False)
    with pytest.raises(BrontoConfigError) as excinfo:
        BrontoClient.from_env()
    assert "BRONTO_REGION" in str(excinfo.value)


def test_caller_supplied_http_client_is_not_closed(recorder: RequestRecorder):
    http = httpx.Client(transport=make_transport(recorder))
    client = BrontoClient(api_key="k", base_url=BASE_URL, http_client=http)
    client.close()
    assert not http.is_closed
    http.close()


def test_owned_http_client_is_closed():
    client = BrontoClient(api_key="k", base_url=BASE_URL)
    http = client._http
    client.close()
    assert http.is_closed


def test_context_manager_closes_owned_client():
    with BrontoClient(api_key="k", base_url=BASE_URL) as client:
        http = client._http
    assert http.is_closed


def test_redirect_is_not_followed(recorder: RequestRecorder):
    def redirecting(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(request)
        return httpx.Response(302, headers={"Location": "https://evil.example.com/"})

    transport = httpx.MockTransport(redirecting)
    client = BrontoClient(
        api_key="k", base_url=BASE_URL, http_client=httpx.Client(transport=transport)
    )
    # A 302 surfaces as a mapped error, not a followed redirect. Exactly one
    # request must have been made — the SDK never chased the Location.
    with pytest.raises(BrontoAPIError) as excinfo:
        client.get("/search")
    assert excinfo.value.status_code == 302
    assert len(recorder.requests) == 1
    client.close()
