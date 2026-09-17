set quiet

# The recipes below all run through `uv run`, which warns when an unrelated
# VIRTUAL_ENV is active (a global default venv on the developer's machine) and
# then ignores it. Clearing it for the duration of a recipe keeps the output
# readable and makes the project's own .venv unambiguously the one in use.
export VIRTUAL_ENV := ""

_default:
    just --list --unsorted

# ⭐ run format, lint, typecheck, the spec and version gates, and tests
prepare: format lint typecheck check-spec check-version test

# ⭐ run all unit tests
[positional-arguments]
test *args:
    # configured in pyproject.toml
    uv run pytest "$@"

# run a single test by name (coverage off — the report is noise for one test)
test-one test_name:
    uv run pytest -k "{{ test_name }}" --no-cov

# ⭐ check for potential mistakes
lint:
    uv run ruff check .

# verify types; src/bronto_sdk is held to strict (see pyproject.toml)
typecheck:
    # suppress pyright's version-update chatter
    PYRIGHT_PYTHON_IGNORE_WARNINGS=1 uv run pyright

# ⭐ format all code
format:
    uv run ruff format .

# verify formatting, but don't modify files
format-check:
    uv run ruff format . --check

# verify the vendored OpenAPI spec matches its recorded digest
check-spec:
    scripts/spec-verify.sh --self-test

# record the current vendored spec digest — commit alongside the spec change
spec-baseline:
    scripts/spec-verify.sh --record

# verify VERSION, _version.py and pyproject.toml agree (optionally with a tag)
check-version tag="":
    scripts/version-check.sh --self-test {{ tag }}

# verify the built artifacts: wheel ships py.typed, sdist ships nothing internal
check-dist:
    scripts/dist-check.sh

# print the CHANGELOG section a release would publish — preview before tagging
release-notes version:
    scripts/release-notes.sh {{ version }}

# build the package for upload
build:
    rm -rf dist
    uv run python -m build
    uv run twine check dist/*
    # twine check reads metadata only; this reads what is actually inside.
    scripts/dist-check.sh

# remove build artifacts and tool caches
clean:
    rm -rf dist build .pytest_cache .ruff_cache .coverage htmlcov
    find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +

# write a new version to VERSION, _version.py and pyproject.toml in one step
update-version version:
    echo "{{ version }}" > VERSION
    perl -pi -e 's|^VERSION = "[.\d\w]+"|VERSION = "{{ version }}"|' src/bronto_sdk/_version.py
    perl -pi -e 's|^version = "[.\d\w]+"|version = "{{ version }}"|' pyproject.toml
    # A perl substitution that matches nothing exits 0, so a partially-applied
    # bump is indistinguishable from a successful one without this check. The
    # [.\d\w]+ pattern matches the value being REPLACED, so writing a version
    # containing '-' or '+' works — and the bump after it silently does not,
    # leaving these two files behind while VERSION moves on.
    scripts/version-check.sh {{ version }}
    echo "Updated to {{ version }} — review the diff, then update CHANGELOG.md"
