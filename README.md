# bronto-sdk

[![CI](https://github.com/bronto-community/bronto-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/bronto-community/bronto-sdk-python/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/bronto-community/bronto-sdk-python/badge)](https://scorecard.dev/viewer/?uri=github.com/bronto-community/bronto-sdk-python)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://github.com/bronto-community/bronto-sdk-python)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Python SDK for the [Bronto](https://bronto.io) observability platform.

## Installation

The SDK is not on PyPI. Install the wheel attached to a
[GitHub Release](https://github.com/bronto-community/bronto-sdk-python/releases),
pinned to a version:

```bash
pip install https://github.com/bronto-community/bronto-sdk-python/releases/download/v0.1.0/bronto_sdk-0.1.0-py3-none-any.whl
```

Or build from the tag, which works in a `requirements.txt` because the
requirement is named:

```bash
pip install "bronto-sdk @ git+https://github.com/bronto-community/bronto-sdk-python@v0.1.0"
```

Requires Python 3.11 or newer. The only runtime dependencies are `httpx`,
`pydantic` and `typing_extensions`.

The `langchain` extra is declared but carries no code yet — the name is
reserved so adding it later is not a breaking rename. The `mcp` extra installs
what `bronto_sdk.mcp` needs:

```bash
pip install "bronto-sdk[mcp] @ git+https://github.com/bronto-community/bronto-sdk-python@v0.1.0"
```

## Quickstart

### Sync

```python
from bronto_sdk import BrontoClient
from bronto_sdk.models import SearchRequest

with BrontoClient(api_key="...", region="eu") as client:
    response = client.search.run(
        SearchRequest(
            select=["*", "@raw"],
            from_=["my-collection.my-dataset"],
            time_range="last 30 minutes",
            limit=50,
        )
    )
    for event in response.events or []:
        print(event.time, event.raw)
```

`BrontoClient.from_env()` builds the same client from `BRONTO_API_KEY` plus
either `BRONTO_REGION` or `BRONTO_BASE_URL`.

### Async

`AsyncBrontoClient` is a mirror of `BrontoClient`: **identical method names**,
`async def` bodies. There is no `_async` suffix to remember.

```python
import asyncio

from bronto_sdk import AsyncBrontoClient
from bronto_sdk.models import SearchRequest


async def main() -> None:
    async with AsyncBrontoClient(api_key="...", region="eu") as client:
        response = await client.search.run(
            SearchRequest(select=["count(*)"], from_expr="*", time_range="last 1 hour")
        )
        print(response.totals)


asyncio.run(main())
```

The async client also takes `max_concurrency` (default 20), an
`asyncio.Semaphore` bounding in-flight requests so a fan-out cannot stampede
the API gateway.

## Typed operations

| Call | HTTP | Returns |
| --- | --- | --- |
| `client.search.run(request)` | `POST /search` | `SearchResponse` |
| `client.monitors.list()` | `GET /monitors` | `MonitorsResponse` |
| `client.monitors.retrieve(monitor_id)` | `GET /monitors/{id}` | `Monitor` |
| `client.monitors.events(monitor_id, from_ts=…, to_ts=…)` | `GET /monitors/{id}/events` | `MonitorEventsResponse` |
| `client.datasets.list(from_=…, from_expr=…)` | `GET /datasets` | `DatasetsResponse` |

`search.run()` accepts a `SearchRequest` **or** a plain `dict`, validated on the
way in. Path parameters are URL-quoted.

Response models set `extra="allow"`, so a new server-side field is additive
rather than breaking — it stays reachable through `model_extra`.

### Escape hatches

Typed coverage is narrow on purpose, and a missing endpoint must never block
you on an SDK release:

```python
usage = client.get("/limits", params={"period": "month"})
result = client.post("/analytics/errors", json={"from_ts": 0, "to_ts": 1})
```

Both return the parsed JSON object as a `dict` and go through the same auth,
error mapping and timeout handling as the typed methods. Path joining accepts
`"/search"` and `"monitors/m-1"` alike — exactly one separating slash either way.

## Credentials: two modes

This is the subtlest part of the SDK and the one worth reading before you build
a service on it. A client is **one** of two modes, fixed at construction:

**Client-bound** — built with `api_key` or `bearer_token`. Every call uses it.
Passing a per-request credential raises `BrontoConfigError`: the SDK will not
guess which of two credentials you meant.

```python
client = BrontoClient(api_key="...", region="eu")
client.datasets.list()  # uses the bound key
```

**Per-request** — built with *neither*. The client holds **no** credential, and
every call must supply one:

```python
client = BrontoClient(region="eu")  # holds no credential
client.datasets.list(options={"bearer_token": tenant_jwt})
```

There is **no fallback between the modes**, and a supplied-but-empty
per-request credential fails closed. That is what makes a long-lived
multi-tenant client safe *by construction*: there is no ambient credential on
the client, so there is nothing to leak between tenants.

Within a single origin — one construction, or one request — `bearer_token` wins
over `api_key`. A bearer credential is sent verbatim as `Authorization`; an API
key as `X-BRONTO-API-KEY`.

> A static-key fallback ("use the config key when the request carries none") is
> deliberately *not* in the SDK. A multi-tenant consumer owns that policy in its
> own credential adapter, where it can be reviewed.

## Errors

```
BrontoError
├── BrontoConfigError        bad or missing configuration, unknown region, mode violation
├── BrontoConnectionError    an httpx transport failure (DNS, TLS, timeout)
└── BrontoAPIError           any non-2xx response
    ├── BrontoBadRequestError      400
    ├── BrontoAuthenticationError  401
    ├── BrontoPermissionError      403
    ├── BrontoNotFoundError        404
    ├── BrontoRateLimitError       429  (adds retry_after)
    └── BrontoServerError          5xx
```

Every status-specific class subclasses `BrontoAPIError`, so a broad
`except BrontoAPIError` keeps working as you narrow your handlers.

`BrontoAPIError` carries `status_code`, `correlation_id`, `details`,
`error_type`, `body` and `headers`. `str()` always shows the status and the
correlation id when present — it is the single most useful field when raising a
support ticket, so it is never buried.

```python
from bronto_sdk import BrontoAPIError, BrontoNotFoundError

try:
    monitor = client.monitors.retrieve("m-1")
except BrontoNotFoundError:
    monitor = None
except BrontoAPIError as exc:
    if exc.retryable:  # True for 429 and 5xx
        ...
    raise
```

`retryable` exists so you can write correct retry logic today; the SDK itself
does not retry in v0.1.

**No credential ever reaches an error, a `repr()` or a log line.** Response
headers attached to an error are redacted by key name, and the stored body is
bounded so a large error page cannot bloat a log line.

## Regions and `base_url`

```python
from bronto_sdk import KNOWN_REGIONS, ingest_base_url, rest_base_url, validate_region

rest_base_url("eu")  # https://api.eu.bronto.io
ingest_base_url("eu")  # https://ingestion.eu.bronto.io
```

`KNOWN_REGIONS` is `("eu", "us")` and is **a hint for error messages only, never
an allow-list**. A new region (`us-2`, …) or a staging deployment must work
without an SDK release.

`validate_region` is a **security control, not tidiness.** The region is
interpolated into `https://api.{region}.bronto.io`, so a value containing `/`,
`@`, `.`, `:` or whitespace moves the host off `bronto.io` entirely —
`region="evil.com/"` would yield host `api.evil.com` and send your credential
there. Only the slug pattern `^[a-z0-9][a-z0-9-]*$` is accepted.

`base_url` is **exempt from that validation by design** — it is a full URL and
only ever comes from a trusted source (your own constructor argument or
`BRONTO_BASE_URL`). It wins over `region`. Passing an untrusted `base_url` means
passing an untrusted host, deliberately.

Redirects are **not** followed, and that is a security invariant rather than a
default nobody changed: the API key rides in a *custom* header, which HTTP
clients do not strip on a cross-domain redirect the way they strip
`Authorization`. Turning redirect-following on would hand the key to whatever
host a redirect names.

## Per-request options

`RequestOptions` overrides client configuration for a single call. Absent keys
fall back to the client default; present ones win.

| Key | Effect |
| --- | --- |
| `timeout` | Per-request timeout in seconds (client default: 30.0) |
| `headers` | Extra headers, merged over the SDK's, per-request winning |
| `api_key` | API key for this call — per-request mode only |
| `bearer_token` | Bearer token for this call — per-request mode only |
| `idempotent` | Reserved. **Inert in v0.1**; v0.2's retry logic reads it |

```python
client.search.run(request, options={"timeout": 120.0, "headers": {"X-Trace": tid}})
```

`headers` is applied last and is **not** a credential channel: values there go
out verbatim, so putting an auth header in it bypasses the credential resolver
on purpose.

## Domain helpers

`bronto_sdk.domain` is pure Bronto knowledge — no I/O, no client needed.

### Time ranges

```python
from bronto_sdk.domain import iso_to_ms, ms_to_iso, parse_time_range, parse_window

iso_to_ms("2026-09-16T10:00:00Z")  # 1789552800000
parse_time_range("last 30 minutes")  # (from_ms, to_ms) absolute bounds
parse_window("2 hours ago")  # 7200000 — the duration projection
```

`parse_time_range` mirrors the server-side reference implementation, so the SDK
and the query engine agree on what a phrase means. It handles calendar phrases
(`today`, `yesterday`, `this week`, `previous quarter`, `this quarter last
year`, …) as well as the `last N <unit>` and `N <unit> [ago]` forms, with digit
or spelled-out counts. Pass `ref=` to pin "now" in a test. It raises
`ValueError` on input it cannot parse — never a silent wrong answer.

`ms_to_iso` uses integer arithmetic throughout, so sub-second precision and
large epoch-millisecond values survive intact.

### Query escaping

```python
from bronto_sdk.domain import quote_attribute, quote_value, wildcard_pattern

quote_value("O'Brien")  # 'O''Brien'   — a string literal
quote_attribute('a"b')  # "a""b"       — an attribute reference
```

**The SDK never auto-escapes.** Nothing in the client or the resource layer
rewrites a where clause you supply — the contract is that you pass valid,
already-escaped query text. These helpers exist so that when you embed an
*untrusted* value (model output, user input) you escape it **explicitly at the
call site**, where a reviewer can see it:

```python
where = f"level='error' AND service={quote_value(untrusted_name)}"
```

Escaping is SQL-style and per quote character: single quotes wrap a string
literal and an embedded `'` doubles; double quotes wrap an attribute reference
and an embedded `"` doubles. **Backslash escaping is not supported by the query
engine** — a `\` is an ordinary character and is left untouched.

### Datasets

```python
from bronto_sdk.domain import project_dataset

project_dataset(raw)  # -> {"log_id": ..., "name": ..., "collection": ...}
```

Reads both live shapes: the REST API returns `id` and `dataset`, the MCP tools
return `log_id` and `name`. They are genuinely different — do not assume one.

## MCP endpoint registry

v0.1 ships the endpoint knowledge only, so consumers stop hardcoding the host.
There is **no session opener yet** (that is v0.2, behind the `[mcp]` extra) and
no `mcp` or `langchain` import anywhere in the package.

```python
from bronto_sdk import mcp

mcp.url("eu")  # https://mcp.eu.bronto.io/mcp
mcp.url(base_url="https://mcp.eu.staging.bronto.io")  # …staging.bronto.io/mcp
mcp.auth_headers(api_key="...")  # {"X-BRONTO-API-KEY": "..."}
mcp.auth_headers(bearer_token="...")  # {"Authorization": "..."}
```

`url()` follows the same `region` / `base_url` precedence as the clients, so
both answer the same input identically. `auth_headers()` reuses the clients'
credential resolution rather than restating it: bearer wins, and it fails closed
rather than ever returning an unauthenticated dict.

The header dict is meant to go onto the `httpx` client the MCP transport is
built on, which is how the streamable-HTTP client takes headers.

## Development

```bash
uv sync          # create .venv and install dev dependencies
just prepare     # format, lint, typecheck, spec digest gate, tests
```

`just prepare` must be green before every commit. Run `just --list` to see
every recipe, and see [CONTRIBUTING.md](CONTRIBUTING.md) for the full setup.

Runnable versions of everything above live in [`examples/`](examples/).

## License

MIT — see [LICENSE](LICENSE).
