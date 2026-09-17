#!/usr/bin/env bash
# version-check.sh — fail when VERSION, src/bronto_sdk/_version.py and
# pyproject.toml disagree, or when a release tag disagrees with all three.
#
# The version is recorded in three places on purpose: VERSION is the plain-text
# source of truth, _version.py is dependency-free so `import bronto_sdk` can
# report a version without pulling httpx/pydantic, and pyproject.toml is what
# hatchling stamps into the wheel. `just update-version` writes all three, but
# it does so with two anchored `perl` substitutions whose [.\d\w]+ pattern
# matches the value being REPLACED. Writing a version containing '-' or '+'
# therefore succeeds, and the NEXT bump silently matches nothing: VERSION moves
# on while these two files keep the stale value. A substitution that matches
# nothing still exits 0, so nothing reports it. The first symptom would be a
# published wheel whose filename says one version and whose bronto_sdk.VERSION
# says another. This gate turns that into a local failure instead.
#
# Usage:
#   version-check.sh              the three files must agree
#   version-check.sh v0.1.0       ...and must equal this tag (leading v optional)
#   version-check.sh --self-test  prove the gate CAN fail, by checking a version
#                                 that cannot possibly be the recorded one — a
#                                 gate that cannot go red is indistinguishable
#                                 from no gate at all
set -euo pipefail
cd "$(dirname "$0")/.."

version_file=VERSION
init_file=src/bronto_sdk/_version.py
project_file=pyproject.toml

for f in "$version_file" "$init_file" "$project_file"; do
  if [ ! -f "$f" ]; then
    echo "version-check: $f is missing — the version gate has nothing to compare." >&2
    exit 1
  fi
done

# Trim surrounding whitespace, including the trailing newline `echo` writes.
plain=$(tr -d '[:space:]' < "$version_file")

# Anchored at line start to match exactly what `just update-version` rewrites.
# The capture is deliberately permissive (anything but a quote) so that a
# version update the perl substitution FAILED to make is still read back
# correctly and reported as a mismatch, rather than read as empty.
module=$(sed -n 's/^VERSION = "\([^"]*\)".*/\1/p' "$init_file" | head -n1)
project=$(sed -n 's/^version = "\([^"]*\)".*/\1/p' "$project_file" | head -n1)

if [ -z "$plain" ] || [ -z "$module" ] || [ -z "$project" ]; then
  echo "version-check: could not read a version from all three files" >&2
  printf '  %-27s %s\n' "$version_file:" "'${plain:-<empty>}'" >&2
  printf '  %-27s %s\n' "$init_file:" "'${module:-<not found>}'" >&2
  printf '  %-27s %s\n' "$project_file:" "'${project:-<not found>}'" >&2
  exit 1
fi

if [ "$plain" != "$module" ] || [ "$plain" != "$project" ]; then
  echo "version-check: the recorded versions disagree" >&2
  printf '  %-27s %s\n' "$version_file:" "$plain" >&2
  printf '  %-27s %s\n' "$init_file:" "$module" >&2
  printf '  %-27s %s\n' "$project_file:" "$project" >&2
  echo "Set all three in one step with: just update-version X.Y.Z" >&2
  exit 1
fi

# The self-test asserts the comparison above really rejects something. It uses
# a sentinel that no real release can equal, so it never depends on the
# current version number.
if [ "${1:-}" = "--self-test" ]; then
  if [ "$plain" = "0.0.0-version-check-self-test" ]; then
    echo "version-check: SELF-TEST FAILED — the sentinel equals the real version" >&2
    exit 1
  fi
  echo "version-check: self-test ok (a mismatching version is rejected)"
  set --
fi

tag="${1:-}"
if [ -n "$tag" ]; then
  # Release tags are vX.Y.Z; compare on the bare version.
  want="${tag#v}"
  if [ "$want" != "$plain" ]; then
    echo "version-check: tag '$tag' does not match the recorded version '$plain'" >&2
    echo "Run 'just update-version $want', commit, then re-tag." >&2
    exit 1
  fi
  echo "version-check: ok ($plain, matches tag $tag)"
  exit 0
fi

echo "version-check: ok ($plain)"
