#!/usr/bin/env bash
# spec-verify.sh — fail when api/openapi.yaml no longer matches the digest
# recorded in api/vendored.sha256.
#
# The vendored spec is a CONFORMANCE REFERENCE, never a codegen source: the
# SDK's request/response shapes are hand-written. That makes accidental drift
# invisible without a gate — nothing rebuilds and nothing fails. A recorded
# digest makes any edit to api/openapi.yaml, accidental or a deliberate
# re-vendor, come with a matching api/vendored.sha256 update in the same commit
# (`just spec-baseline`), which is the reviewable governance step.
#
# Usage:
#   spec-verify.sh              verify the digest
#   spec-verify.sh --self-test  additionally prove the gate CAN fail by hashing
#                               a tampered copy and requiring a mismatch — a
#                               gate that cannot go red is indistinguishable
#                               from no gate at all
#   spec-verify.sh --record     write the current digest to the record
#                               (just spec-baseline)
set -euo pipefail
cd "$(dirname "$0")/.."

spec=api/openapi.yaml
record=api/vendored.sha256

sha() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d' ' -f1
  else
    echo "spec-verify: neither sha256sum nor shasum available" >&2
    exit 1
  fi
}

if [ ! -f "$spec" ]; then
  echo "spec-verify: $spec is missing — the vendored spec is part of the repo." >&2
  exit 1
fi

got=$(sha "$spec")

if [ "${1:-}" = "--record" ]; then
  printf '%s  vendored %s\n' "$got" "$(date -u +%Y-%m-%d)" > "$record"
  echo "spec-verify: recorded $got in $record — commit this alongside the api/openapi.yaml change"
  exit 0
fi

if [ ! -f "$record" ]; then
  echo "spec-verify: $record is missing — the spec gate has nothing to verify against." >&2
  echo "Record the current vendored digest with: just spec-baseline" >&2
  exit 1
fi

if [ "${1:-}" = "--self-test" ]; then
  tmp=$(mktemp)
  trap 'rm -f "$tmp"' EXIT
  cp "$spec" "$tmp"
  printf '\n# spec-verify self-test tamper line\n' >> "$tmp"
  if [ "$(sha "$tmp")" = "$got" ]; then
    echo "spec-verify: SELF-TEST FAILED — tampering did not change the digest; this gate cannot fail" >&2
    exit 1
  fi
fi

want=$(cut -d' ' -f1 < "$record")
if [ "$got" != "$want" ]; then
  echo "spec-verify: api/openapi.yaml does not match the recorded vendored digest" >&2
  echo "  recorded: $want  ($record)" >&2
  echo "  actual:   $got" >&2
  echo "If this edit is intentional (re-vendor or patch), update the record in the same commit: just spec-baseline" >&2
  exit 1
fi
echo "spec-verify: ok ($got)"
