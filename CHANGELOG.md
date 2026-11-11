# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Breaking changes are listed first with a ⚠️ prefix.

## [Unreleased]

## [0.2.1] - 2026-11-11

### Added

- **Published on [PyPI](https://pypi.org/project/bronto-sdk/)** — install with
  `pip install bronto-sdk` (or `bronto-sdk[mcp]`) instead of a GitHub Release
  URL or a `git+https` requirement. Uploads use Trusted Publishing from the
  release workflow (no API token exists) and carry PEP 740 provenance
  attestations; PyPI receives exactly the files that are Sigstore-signed and
  attached to the GitHub Release, which continues as before.
  [SECURITY.md](https://github.com/bronto-community/bronto-sdk-python/blob/main/SECURITY.md#verifying-a-release)
  covers verifying both.

### Security

- Refreshed `uv.lock` to PyJWT 2.15.1 and urllib3 2.8.0. Both reach the lock
  only through the `mcp`/`langchain` extras and dev tooling; the SDK never
  imports them and its published dependency ranges are unchanged, so installed
  users resolve their own versions and are not affected.
- Refreshed `uv.lock` to certifi 2026.10.23, which drops the emSign root CAs
  whose intermediate keys were compromised (GHSA-6q48-6c7w-9gw2). certifi
  reaches the lock only transitively through `httpx`; the SDK's published
  dependency ranges are unchanged, so installed users resolve their own
  certifi and should upgrade it in their own environments.

### Changed

- Refreshed `uv.lock` to pydantic 2.14.1, langchain-core 1.7.3, and newer dev
  tooling (ruff 0.17.3, pytest 9.2.0, pytest-mock 3.17.0, pytest-asyncio
  1.4.1.post1), and bumped the pinned CI actions. Published dependency ranges
  are unchanged.

## [0.2.0] - 2026-09-29

### Added

- **`client.metrics.retrieve_definition(metric_id)`** — `GET
  /metrics/definitions/{id}`, returning a `MetricDefinition`.

## [0.1.2] - 2026-09-18

### Added

- **Signed release artifacts.** The wheel and sdist are now signed with
  [Sigstore](https://www.sigstore.dev/) during the release workflow, and a
  `.sigstore.json` bundle is attached to the release beside each one. Signing is
  keyless: the signature is made with a short-lived identity minted for that one
  workflow run, so there is no signing key to hold and the repository still
  stores no secrets. The signature attests that an artifact came from this
  repository's release workflow running on the tag it claims.

  Verifying needs only pip — `pip install sigstore`, then
  `python -m sigstore verify identity`. [SECURITY.md](SECURITY.md) has the full
  command. The release workflow verifies its own signatures before publishing,
  so an artifact whose signature does not check never reaches a release.

### Note

- `v0.1.1` was tagged but never released: its release workflow failed while
  signing, before anything was published. The tag is left in place because
  release tags are immutable here. There is no v0.1.1 release, and nothing was
  ever published under it.

## [0.1.0] - 2026-09-17

First release. Everything below is new.

### Added

- **Clients.** `BrontoClient` (sync) and `AsyncBrontoClient` (async) over
  `httpx`, with identical method names, context-manager support, `close()` /
  `aclose()`, and `from_env()` reading `BRONTO_API_KEY` plus `BRONTO_REGION` or
  `BRONTO_BASE_URL`. A caller-supplied `http_client` is never closed by the SDK.
  The async client adds a `max_concurrency` semaphore (default 20) bounding
  in-flight requests. `client.get()` / `client.post()` remain public escape
  hatches so an uncovered endpoint never blocks a consumer on an SDK release.
- **Two-mode credentials.** A client is either *client-bound* (built with
  `api_key` or `bearer_token`) or *per-request* (built with neither, holding no
  credential). The modes never mix and there is no fallback between them, which
  makes a long-lived multi-tenant client safe by construction. Bearer wins over
  API key within one origin; an empty per-request credential fails closed.
- **Error hierarchy.** `BrontoError`, `BrontoConfigError`,
  `BrontoConnectionError` and `BrontoAPIError`, with status-mapped subclasses
  for 400, 401, 403, 404, 429 (carrying `retry_after`) and 5xx. Errors expose
  `status_code`, `correlation_id`, `details`, `error_type`, `body`, `headers`
  and a `retryable` flag; `str()` always surfaces the status and correlation id.
  No credential reaches an error, a `repr()` or a log line — headers are
  redacted by key name and the stored body is bounded.
- **Regional registry.** `validate_region`, `rest_base_url`, `mcp_url` and
  `ingest_base_url`. Region is a validated slug rather than a closed enum, so a
  new region works without an SDK release while a value that would smuggle a
  host off `bronto.io` is rejected. `KNOWN_REGIONS` is a hint for error
  messages, never an allow-list. Redirects are not followed, deliberately.
- **Per-request options.** `RequestOptions` for `timeout`, `headers`, a
  per-request credential, and an `idempotent` flag reserved for v0.2 retries.
- **`bronto_sdk.models`:** Pydantic v2 models for the covered REST subset —
  `SearchRequest`/`SearchResponse`, `Monitor`/`MonitorsResponse`,
  `MonitorEventsResponse`, `Dataset`/`DatasetsResponse` and `ErrorResponse`.
  Response models accept unknown fields so a new server-side field is additive,
  and no sequence number or epoch-millisecond field is typed `float`.
- **`bronto_sdk.resources`:** the typed operation surface, wired onto both
  clients as `client.search`, `client.monitors` and `client.datasets` —
  `search.run()`, `monitors.list()`, `monitors.retrieve()`, `monitors.events()`
  and `datasets.list()`, each returning a parsed model. Path parameters are
  URL-quoted.
- **`bronto_sdk.domain`:** pure Bronto helpers with no I/O. `iso_to_ms`,
  `ms_to_iso`, `parse_time_range` and `parse_window` resolve natural-language
  windows the way the query engine does, with no `dateparser` dependency;
  `quote_value`, `quote_attribute` and `wildcard_pattern` escape values for a
  where clause — **opt-in, never automatic**; `project_dataset` reads both the
  REST and MCP dataset shapes.
- **`bronto_sdk.mcp`:** the MCP endpoint registry — `url()` (by region, or by
  `base_url` for a staging deployment the region slug cannot name) and
  `auth_headers()`. String and dict helpers only: no `mcp` or `langchain`
  import, and no session opener until v0.2.
- Documentation: a full README with quickstarts, the credential model, the
  error hierarchy, the domain helpers and a migration table from an ad-hoc
  client, plus four runnable scripts in `examples/`.

### Not in this release

Automatic retries and backoff, pagination iterators, an MCP session opener,
LangChain tool decorators, OpenTelemetry hooks, an ingestion client (URL helper
only), and REST coverage beyond the five operations above.

[Unreleased]: https://github.com/bronto-community/bronto-sdk-python/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/bronto-community/bronto-sdk-python/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/bronto-community/bronto-sdk-python/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/bronto-community/bronto-sdk-python/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/bronto-community/bronto-sdk-python/releases/tag/v0.1.0
