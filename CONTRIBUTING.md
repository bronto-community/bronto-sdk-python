# Contributing to bronto-sdk

We welcome bug reports, feature requests, and pull requests. For anything that
changes the public API or introduces substantial code, please open (or find) an
issue first so we can agree on an approach before you write the code. Typo and
documentation fixes do not need an issue.

## 5-minute path

```sh
git clone https://github.com/bronto-community/bronto-sdk-python
cd bronto-sdk-python
uv sync          # create .venv and install the project + dev dependencies
just prepare     # format, lint, typecheck, spec digest gate, tests
```

No network access or Bronto account is needed to run the test suite. All HTTP is
mocked with `httpx.MockTransport`, so the fast suite never touches the network.

## Development environment

- **[`uv`](https://docs.astral.sh/uv/)** manages the virtual environment and
  dependencies. `uv sync` creates `.venv` and installs everything; commit
  `uv.lock` whenever dependencies change so CI stays reproducible.
- **[`just`](https://just.systems/)** runs every project command through
  `uv run`. `just --list` shows the recipes; the important ones are below.
- Minimum supported Python is **3.11**. Local development happens on the newest
  interpreter, but `pyright` and `ruff` are pinned to the 3.11 floor so
  3.12+-only syntax cannot slip past and break the oldest CI leg.

| Task | Command |
| --- | --- |
| Everything CI runs | `just prepare` |
| Format | `just format` / `just format-check` |
| Lint | `just lint` |
| Typecheck (pyright strict on `src/bronto_sdk`) | `just typecheck` |
| Tests | `just test` / `just test-one <name>` |
| Build sdist + wheel | `just build` |
| Verify the vendored spec digest | `just check-spec` |
| Verify the three version files agree | `just check-version` |
| Verify the built artifacts | `just check-dist` |
| Preview a release body | `just release-notes X.Y.Z` |

## Tests

- Prefer test-driven development for new behavior.
- Use `pytest`, `pytest-mock`, and `pytest-asyncio` (`asyncio_mode = "auto"`).
- Mock all HTTP with `httpx.MockTransport`; the fast suite must not hit the
  network.
- Sync and async clients expose identical method names — cover new client
  behavior with the shared sync/async parity fixtures so both stay in step.
- Coverage target is 90%+, realistic given the small surface.

## The vendored OpenAPI spec

`api/openapi.yaml` is a conformance reference, never a codegen source. It is
digest-gated: any edit must ship with a regenerated `api/vendored.sha256` in the
same commit. See `api/README.md` for the full re-vendoring checklist. `just
check-spec` (part of `just prepare` and CI) fails on an unrecorded edit.

## Changelog

User-facing changes must add an entry under `## [Unreleased]` in
`CHANGELOG.md` (Keep a Changelog format). List breaking changes first with a
`⚠️` prefix. The pull request template has a `## Changelog` section for the same
purpose.

## Versioning

Semver from day one. `v0.x` means the public API may still shift; breaking
changes are called out with `⚠️` in the changelog. Bump the version with
`just update-version X.Y.Z`, which writes `VERSION`, `src/bronto_sdk/_version.py`
and `pyproject.toml` in one step.

## Releasing (maintainers)

Releases are **GitHub Releases**, not PyPI. A `vX.Y.Z` tag push runs
`release.yml`, which builds the sdist and wheel and attaches both to a release
consumers install from. Publishing to PyPI is deliberately off; the note at the
foot of `.github/workflows/release.yml` records how to turn it on.

To cut a release:

1. Move the `## [Unreleased]` entries under a new `## [X.Y.Z] - YYYY-MM-DD`
   heading in `CHANGELOG.md`, and add the link reference at the bottom. The
   release body is extracted from this section, so a missing or empty one fails
   the release — preview it with `just release-notes X.Y.Z`.
2. `just update-version X.Y.Z`. It verifies its own work; a version it cannot
   write to all three files is now an error rather than a silent no-op.
3. `just prepare`, then commit.
4. Tag `vX.Y.Z` and push the tag.

The workflow gates the release on the tag matching the version files, then on
the same lint/test/build checks a pull request runs — literally the same file,
`.github/workflows/_checks.yml`, so a release cannot be verified on less than a
pull request is.

**Rehearse before the real tag.** Run `release.yml` from `main` via
`workflow_dispatch` to exercise everything except release creation, and push a
pre-release tag (`v0.1.0rc1`) to exercise release creation itself — a tag whose
version has a letter in it is published as a GitHub pre-release. Delete the
rehearsal release and tag afterwards.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating you agree to abide by it.
