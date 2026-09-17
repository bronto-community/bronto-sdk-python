# Agent instructions

`bronto-sdk` is a small, hand-written Python SDK for the Bronto observability
platform: a typed REST client (sync + async), pure Bronto domain helpers, and an
MCP endpoint registry. It wraps a deliberately narrow slice of the Bronto REST
API. It is read as much as it is run — when a feature and a first-time reader's
understanding compete, the reader wins.

## Code style

- Keep data and behavior separate. Use Pydantic models, `TypedDict`, or
  `dataclass` for shapes; plain module-level functions for helpers; classes only
  where real state exists (clients, errors).
- No global mutable state. A client instance is the only entry point; importing
  `bronto_sdk` has zero side effects.
- Private by default: modules are `_`-prefixed. Only `bronto_sdk/__init__.py`
  and the documented `domain`, `models`, and `mcp` subpackages re-export public
  API.
- Sync and async are mirrors: `BrontoClient` and `AsyncBrontoClient` expose
  identical method names. Shared request-building and response-parsing logic
  lives in pure functions used by both, so a bug is fixed in one place.
- Fully typed. `py.typed` ships; `pyright` is strict on `src/bronto_sdk`; every
  public symbol has a docstring (Google convention).
- Comments explain WHY, not WHAT.
- Never let a credential reach an error, `repr()`, or log line; never let a big
  integer (sequence numbers, epoch-ms) be typed `float`.

## Testing

- Use `pytest`, `pytest-mock`, and `pytest-asyncio` (`asyncio_mode = "auto"`).
- Mock all HTTP with `httpx.MockTransport` — no network in the fast suite.
- Cover client behavior through the shared sync/async parity fixtures so both
  clients stay identical.
- Prefer TDD for new behavior; keep assertions exact (golden values, not just
  "no error").

## Packaging & commands

- `uv` manages the environment; `just` runs everything through `uv run`.
- `uv sync` sets up `.venv`; commit `uv.lock` when dependencies change.
- `just prepare` runs format, lint, typecheck, the spec digest gate, and tests —
  it must be green before every commit.
- `just build` produces the sdist + wheel and runs `twine check`.
- `just update-version X.Y.Z` is the only way to change the version (it writes
  `VERSION`, `_version.py`, and `pyproject.toml` together).

## Key locations

- `src/bronto_sdk/` — the package; `_`-prefixed modules are private.
- `src/bronto_sdk/{domain,models,mcp}/` — the public subpackages.
- `tests/` — `unit/`, `domain/`, and `mcp/` suites; `conftest.py` holds shared
  fixtures.
- `api/openapi.yaml` — the vendored spec (conformance reference, digest-gated,
  never a codegen source). See `api/README.md`.

## Context hygiene

- Keep this file concise and evergreen. No long code examples, no dated
  ecosystem claims, no secrets, no aspirational features until they are active
  work.
- Code destined to move (e.g. into a consumer) lives in modules named for that
  fate, so moving it stays a deletion rather than surgery.
