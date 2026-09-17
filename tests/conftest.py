"""Shared fixtures for the test suite.

The mock-transport client fixtures and the parametrised sync/async ``parity``
fixture live here so both clients are exercised through one call adapter and no
test ever has to reach for a path-manipulating import hack.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

from bronto_sdk import AsyncBrontoClient, BrontoClient

# tests/ -> repo root. Used by the version smoke test to read the VERSION file
# without hardcoding a relative path that breaks depending on the working
# directory pytest was invoked from.
REPO_ROOT = Path(__file__).resolve().parent.parent

BASE_URL = "https://api.eu.bronto.io"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


@dataclass
class RequestRecorder:
    """Captures the requests a mock transport sees, for later assertions.

    Attributes:
        requests: Every request the transport handled, in order.
    """

    requests: list[httpx.Request] = field(default_factory=list)

    @property
    def last(self) -> httpx.Request:
        """Return the most recent request the transport handled."""
        return self.requests[-1]


def make_transport(
    recorder: RequestRecorder,
    *,
    status_code: int = 200,
    json_body: Any = None,
    headers: dict[str, str] | None = None,
    text: str | None = None,
) -> httpx.MockTransport:
    """Build a ``MockTransport`` that records requests and returns a canned reply.

    Args:
        recorder: The recorder to append each handled request to.
        status_code: The status code to return.
        json_body: A JSON-serialisable body; ignored when ``text`` is given.
        headers: Response headers to return.
        text: A raw body string, used instead of ``json_body`` when set.

    Returns:
        A configured ``httpx.MockTransport``.
    """
    body = (
        text if text is not None else json.dumps({} if json_body is None else json_body)
    )

    def handler(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(request)
        return httpx.Response(status_code, headers=headers, text=body)

    return httpx.MockTransport(handler)


@dataclass
class ClientHarness:
    """A uniform adapter driving either client through one test body.

    ``get``/``post``/``close`` hide the sync-vs-async difference: the async
    variant runs every call on one persistent event loop so a client's
    concurrency semaphore stays bound to a single loop across calls.

    Attributes:
        kind: ``"sync"`` or ``"async"``.
        loop: The event loop async calls run on, or ``None`` for the sync kind.
    """

    kind: str
    loop: asyncio.AbstractEventLoop | None = None

    def build(self, transport: httpx.MockTransport, **kwargs: Any) -> Any:
        """Construct a client over ``transport`` with the given constructor args."""
        if self.kind == "async":
            return AsyncBrontoClient(
                http_client=httpx.AsyncClient(transport=transport), **kwargs
            )
        return BrontoClient(http_client=httpx.Client(transport=transport), **kwargs)

    def _run(self, value: Any) -> Any:
        """Resolve an awaitable on the harness loop; pass sync values through."""
        if self.loop is not None and asyncio.iscoroutine(value):
            return self.loop.run_until_complete(value)
        return value

    def get(self, client: Any, path: str, **kwargs: Any) -> dict[str, object]:
        """Perform ``client.get`` uniformly across both clients."""
        return self._run(client.get(path, **kwargs))

    def post(self, client: Any, path: str, **kwargs: Any) -> dict[str, object]:
        """Perform ``client.post`` uniformly across both clients."""
        return self._run(client.post(path, **kwargs))

    def call(self, value: Any) -> Any:
        """Resolve a resource-method result uniformly across both clients.

        The sync resources return a value and the async ones a coroutine, so a
        parity test writes ``parity.call(client.search.run(req))`` once and both
        kinds are driven by the same body.
        """
        return self._run(value)

    def close(self, client: Any) -> None:
        """Close a client uniformly across both clients."""
        if self.kind == "async":
            self._run(client.aclose())
        else:
            client.close()


@pytest.fixture(params=["sync", "async"])
def parity(request: pytest.FixtureRequest) -> Any:
    """Yield a :class:`ClientHarness` once per client kind for parity tests."""
    if request.param == "async":
        loop = asyncio.new_event_loop()
        try:
            yield ClientHarness("async", loop)
        finally:
            loop.close()
    else:
        yield ClientHarness("sync")


@pytest.fixture
def recorder() -> RequestRecorder:
    """Return a fresh request recorder."""
    return RequestRecorder()
