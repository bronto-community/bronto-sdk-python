#!/usr/bin/env bash
# dist-check.sh — fail when the built artifacts are not what we mean to publish.
#
# Two failure modes this catches, neither of which `twine check` sees, because
# twine validates metadata and never looks inside:
#
# 1. A wheel missing py.typed. It is a zero-byte marker that no test imports,
#    so nothing else in this repo would notice its absence — pyright checks the
#    source tree, never the wheel. Without it, every downstream user's type
#    checking silently degrades to Any, and the first report comes from a
#    consumer. That marker is the SDK's whole "Typing :: Typed" claim.
#
# 2. An sdist carrying files that were never meant to leave the machine. The
#    0.1.0 sdist shipped an internal planning document, .vscode/ and .github/,
#    because hatchling's default is "everything git does not ignore". The
#    explicit manifest in pyproject.toml fixes it; this gate is what stops it
#    coming back, since the sdist is attached to every GitHub Release.
#
# Usage:
#   dist-check.sh          check the artifacts in dist/
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(tr -d '[:space:]' < VERSION)

wheels=$(find dist -maxdepth 1 -name '*.whl' 2>/dev/null || true)
sdists=$(find dist -maxdepth 1 -name '*.tar.gz' 2>/dev/null || true)

if [ -z "$wheels" ] || [ -z "$sdists" ]; then
  echo "dist-check: dist/ must hold a wheel and an sdist — run 'just build' first." >&2
  exit 1
fi

# More than one of either means a stale artifact from an earlier version is
# still lying around, and `gh release create dist/*` would upload it.
if [ "$(printf '%s\n' "$wheels" | grep -c .)" -ne 1 ] \
  || [ "$(printf '%s\n' "$sdists" | grep -c .)" -ne 1 ]; then
  echo "dist-check: expected exactly one wheel and one sdist in dist/, found:" >&2
  printf '%s\n' "$wheels" "$sdists" | sed 's/^/  /' >&2
  echo "'just build' removes dist/ first; a stale file here means it was added by hand." >&2
  exit 1
fi

for artifact in $wheels $sdists; do
  case "$(basename "$artifact")" in
    *"$version"*) ;;
    *)
      echo "dist-check: $artifact is not named for the current version ($version)" >&2
      echo "This is a build of a different tree than VERSION describes." >&2
      exit 1
      ;;
  esac
done

# --- the wheel -------------------------------------------------------------
wheel_names=$(python3 -m zipfile -l "$wheels" | awk 'NR>1 && NF {print $1}')

if ! printf '%s\n' "$wheel_names" | grep -qx 'bronto_sdk/py\.typed'; then
  echo "dist-check: $wheels is missing bronto_sdk/py.typed" >&2
  echo "The SDK advertises inline types (Typing :: Typed); without this marker" >&2
  echo "type checkers ignore every annotation it ships." >&2
  exit 1
fi

if ! printf '%s\n' "$wheel_names" | grep -qx 'bronto_sdk/__init__\.py'; then
  echo "dist-check: $wheels does not contain bronto_sdk/__init__.py" >&2
  exit 1
fi

# Exactly the package and its metadata directory, nothing else.
unexpected=$(printf '%s\n' "$wheel_names" | cut -d/ -f1 | sort -u \
  | grep -v '^bronto_sdk$' | grep -v '\.dist-info$' | grep -v '^$' || true)
if [ -n "$unexpected" ]; then
  echo "dist-check: $wheels has unexpected top-level entries:" >&2
  printf '%s\n' "$unexpected" | sed 's/^/  /' >&2
  exit 1
fi

# --- the sdist -------------------------------------------------------------
# Strip the leading `bronto_sdk-X.Y.Z/` component so the patterns below read as
# repository paths.
sdist_names=$(tar tzf "$sdists" | cut -d/ -f2- | grep -v '^$')

# Anything matching these must never be published. Kept as an explicit deny
# list alongside pyproject.toml's allow list: the manifest states intent, this
# states the consequence of getting it wrong, and a reader sees both.
forbidden='(^|/)(\.github|\.vscode|\.venv|\.git|dist|htmlcov)(/|$)|plan\.md$|^CLAUDE\.md$|^AGENTS\.md$|\.env$'
leaked=$(printf '%s\n' "$sdist_names" | grep -E "$forbidden" || true)
if [ -n "$leaked" ]; then
  echo "dist-check: the sdist contains files that must not be published:" >&2
  printf '%s\n' "$leaked" | sed 's/^/  /' >&2
  echo "Fix [tool.hatch.build.targets.sdist] in pyproject.toml." >&2
  exit 1
fi

if ! printf '%s\n' "$sdist_names" | grep -q '^src/bronto_sdk/__init__\.py$'; then
  echo "dist-check: the sdist does not contain src/bronto_sdk/__init__.py" >&2
  exit 1
fi

echo "dist-check: ok (wheel $(printf '%s\n' "$wheel_names" | grep -c .) files with py.typed; sdist $(printf '%s\n' "$sdist_names" | grep -c .) files, no internal paths)"
