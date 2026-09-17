# Vendored Bronto OpenAPI spec

`openapi.yaml` is the Bronto API specification (OpenAPI 3.0.2), vendored into
this repository as a **conformance reference only**.

## It is never a codegen source

The SDK's request builders and response models are hand-written. v0.1 covers
four operations; generating ~200 modules from this spec would be pure overhead
and would commit the project to a pipeline it does not have. The spec is here so
that a reviewer can check a hand-written shape against the contract without
leaving the repo, and so that a spec revision is a reviewable diff.

## Provenance

| Field | Value |
| --- | --- |
| Vendored from | [`bronto-cli`](https://github.com/bronto-community/bronto-cli) @ `72a9f0a363ec5939120bd7041b09275930e0142c` (2026-09-04) |
| Source path | `api/openapi.yaml` in that repo |
| Vendored digest | `4d5d01f7b9bbc5ca5d5ce03b5f9d5e4587a1c93e8aa29c033b85950b9a8397a8` |
| Upstream digest at vendoring time | see `upstream.sha256` |

Copied byte-for-byte from the Go sibling rather than re-downloaded, so both
repositories reference an identical revision and can be compared by digest
alone. Note that `bronto-cli` patches the spec after vendoring, which is why the
vendored digest differs from the upstream one — `vendored.sha256` records the
file as it exists here, `upstream.sha256` records the unpatched upstream.

## The digest gate

`vendored.sha256` records the digest of `openapi.yaml` as committed.
`scripts/spec-verify.sh` (wired into `just prepare` and CI as `just check-spec`)
fails when the two disagree.

Any edit to the spec — an accidental one or a deliberate re-vendor — must come
with a regenerated record in the same commit:

```bash
just spec-baseline   # rewrites api/vendored.sha256
```

That makes re-vendoring a visible, reviewable act rather than a silent change to
a 17,000-line file.

## Re-vendoring checklist

1. Copy the new spec over `openapi.yaml`.
2. Run `just spec-baseline`.
3. **Re-check any line-number references to the spec.** A spec update shifts
   every one of them. Such references have been wrong before — read from a
   different revision than the one vendored — so treat them as stale until
   re-checked against the new file.
4. Diff the schemas the SDK actually models before trusting them.
