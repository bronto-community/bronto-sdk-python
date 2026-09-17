"""Tests specific to the asynchronous AsyncBrontoClient."""

import asyncio

import httpx
import pytest

from bronto_sdk import AsyncBrontoClient, BrontoAPIError, BrontoConfigError
from tests.conftest import BASE_URL, RequestRecorder, make_transport


async def test_from_env_reads_region(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BRONTO_API_KEY", "env-key")
    monkeypatch.setenv("BRONTO_REGION", "us")
    monkeypatch.delenv("BRONTO_BASE_URL", raising=False)
    client = AsyncBrontoClient.from_env()
    assert client._base_url == "https://api.us.bronto.io"
    await client.aclose()


async def test_from_env_missing_region_names_it(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BRONTO_API_KEY", "env-key")
    monkeypatch.delenv("BRONTO_REGION", raising=False)
    monkeypatch.delenv("BRONTO_BASE_URL", raising=False)
    with pytest.raises(BrontoConfigError) as excinfo:
        AsyncBrontoClient.from_env()
    assert "BRONTO_REGION" in str(excinfo.value)


def test_max_concurrency_must_be_positive():
    with pytest.raises(ValueError):
        AsyncBrontoClient(api_key="k", base_url=BASE_URL, max_concurrency=0)


async def test_caller_supplied_http_client_is_not_closed(recorder: RequestRecorder):
    http = httpx.AsyncClient(transport=make_transport(recorder))
    client = AsyncBrontoClient(api_key="k", base_url=BASE_URL, http_client=http)
    await client.aclose()
    assert not http.is_closed
    await http.aclose()


async def test_owned_http_client_is_closed():
    client = AsyncBrontoClient(api_key="k", base_url=BASE_URL)
    http = client._http
    await client.aclose()
    assert http.is_closed


async def test_context_manager_closes_owned_client():
    async with AsyncBrontoClient(api_key="k", base_url=BASE_URL) as client:
        http = client._http
    assert http.is_closed


async def test_redirect_is_not_followed(recorder: RequestRecorder):
    def redirecting(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(request)
        return httpx.Response(302, headers={"Location": "https://evil.example.com/"})

    transport = httpx.MockTransport(redirecting)
    client = AsyncBrontoClient(
        api_key="k",
        base_url=BASE_URL,
        http_client=httpx.AsyncClient(transport=transport),
    )
    with pytest.raises(BrontoAPIError) as excinfo:
        await client.get("/search")
    assert excinfo.value.status_code == 302
    assert len(recorder.requests) == 1
    await client.aclose()


async def test_max_concurrency_bounds_in_flight_requests():
    # A transport that tracks concurrent entries proves the semaphore caps the
    # number of simultaneous in-flight requests at max_concurrency.
    cap = 3
    state = {"in_flight": 0, "peak": 0}
    gate = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        # Hold the slot until every task that will ever start has started,
        # so the peak reflects the true concurrency ceiling.
        await gate.wait()
        state["in_flight"] -= 1
        return httpx.Response(200, text="{}")

    transport = httpx.MockTransport(handler)
    client = AsyncBrontoClient(
        api_key="k",
        base_url=BASE_URL,
        http_client=httpx.AsyncClient(transport=transport),
        max_concurrency=cap,
    )
    tasks = [asyncio.create_task(client.get("/search")) for _ in range(cap * 3)]
    # Let the scheduler run: only `cap` handlers can be inside the semaphore.
    await asyncio.sleep(0.05)
    assert state["peak"] == cap
    gate.set()
    await asyncio.gather(*tasks)
    await client.aclose()
