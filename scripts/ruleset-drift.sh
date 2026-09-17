#!/usr/bin/env bash
# ruleset-drift.sh — fail when the live branch ruleset no longer requires
# exactly the checks recorded in .github/required-status-checks.txt.
#
# The recorded list is checked against the WORKFLOWS by
# tests/unit/test_required_checks.py, which runs offline on every pull request.
# Nothing offline can check it against the RULESET, because the ruleset lives on
# GitHub and can be edited in the web UI by anyone with admin. That edit is the
# one that actually wedges the repository: GitHub reports a required check no
# job produces as permanently pending rather than failed, so every pull request
# waits forever, and protect-main has no bypass actors — not even an admin can
# merge past it.
#
# Deliberately NOT a pull-request check. A pull request that legitimately
# changes the test matrix must disagree with the live ruleset until the ruleset
# is updated, so gating pull requests on this would fail exactly the ones doing
# the right thing. It runs on a schedule, on pushes to main that touch the
# workflows or the list, and on demand.
#
# Reading rulesets on a public repository needs no authentication, so this needs
# no token and no stored secret. GH_TOKEN is used when present only to spend the
# authenticated rate limit instead of the shared anonymous one.
#
# Usage:
#   ruleset-drift.sh                      check the recorded list
#   ruleset-drift.sh path/to/list.txt     check a different list — point it at a
#                                         tampered copy to prove the gate can go
#                                         red, which is the only property that
#                                         makes a gate worth having
set -euo pipefail
cd "$(dirname "$0")/.."

list="${1:-.github/required-status-checks.txt}"

if [ ! -f "$list" ]; then
  echo "ruleset-drift: $list is missing — there is nothing to compare against." >&2
  exit 1
fi

# GITHUB_REPOSITORY is set inside Actions; fall back to the project URL so the
# script is runnable locally from a fresh clone with no arguments.
repo="${GITHUB_REPOSITORY:-}"
if [ -z "$repo" ]; then
  repo=$(sed -n 's|^source = "https://github.com/\(.*\)"$|\1|p' pyproject.toml | head -n1)
fi
if [ -z "$repo" ]; then
  echo "ruleset-drift: could not determine the repository slug" >&2
  exit 1
fi

fetch() {
  if command -v gh >/dev/null 2>&1 && [ -n "${GH_TOKEN:-}${GITHUB_TOKEN:-}" ]; then
    gh api "$1"
  else
    curl -sSL -H 'Accept: application/vnd.github+json' "https://api.github.com/$1"
  fi
}

# The branch ruleset is found by target rather than by a hardcoded id, so this
# keeps working if the ruleset is ever recreated.
ruleset_id=$(fetch "repos/$repo/rulesets" \
  | python3 -c 'import json,sys; print(next((r["id"] for r in json.load(sys.stdin) if r["target"]=="branch"), ""))')

if [ -z "$ruleset_id" ]; then
  echo "ruleset-drift: $repo has no branch ruleset — main is unprotected." >&2
  exit 1
fi

live=$(fetch "repos/$repo/rulesets/$ruleset_id" | python3 -c '
import json, sys
rules = json.load(sys.stdin)["rules"]
checks = [c["context"]
          for r in rules if r["type"] == "required_status_checks"
          for c in r["parameters"]["required_status_checks"]]
print("\n".join(sorted(checks)))
')

recorded=$(grep -v '^[[:space:]]*#' "$list" | grep -v '^[[:space:]]*$' | sort)

if [ "$live" != "$recorded" ]; then
  echo "ruleset-drift: the live ruleset and $list disagree" >&2
  echo "  < recorded in the repository   > required by the live ruleset" >&2
  diff <(printf '%s\n' "$recorded") <(printf '%s\n' "$live") >&2 || true
  echo >&2
  echo "Update whichever is wrong. If a check was renamed, CONTRIBUTING has the" >&2
  echo "order to do it in — contracting the ruleset first, so no pull request is" >&2
  echo "left waiting on a context nothing reports." >&2
  exit 1
fi

echo "ruleset-drift: ok ($(printf '%s\n' "$recorded" | grep -c .) checks, ruleset $ruleset_id)"
