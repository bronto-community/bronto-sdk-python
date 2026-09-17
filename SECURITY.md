# Security policy

## Supported versions

`bronto-sdk` is pre-1.0. Security fixes are released against the latest
published version only; there are no long-term support branches. Pin a released
version and upgrade forward rather than backporting.

## Reporting a vulnerability

**Please do not open a public issue for a security vulnerability.**

Report it privately through
[GitHub's private vulnerability reporting](https://github.com/bronto-community/bronto-sdk-python/security/advisories/new),
which opens a draft advisory visible only to the maintainers. If you cannot use
that, email **security@bronto.io**.

Please include:

- the version of `bronto-sdk` and of Python you tested against,
- what an attacker gains, in one sentence,
- the smallest reproduction you have — a failing script is ideal,
- any suggested fix, if you have one.

## What to expect

| Stage | Target |
| --- | --- |
| Acknowledgement of your report | 3 working days |
| Initial assessment, with a severity | 10 working days |
| Fix released, or a dated plan if it needs longer | 90 days |

We will keep you updated as the assessment progresses, credit you in the
advisory and the changelog unless you prefer otherwise, and coordinate the
disclosure timing with you. We do not operate a paid bounty.

## Scope

In scope: anything in this repository — the client, the domain helpers, the
models, the MCP endpoint registry, and the release and build tooling under
`.github/` and `scripts/`.

Out of scope: vulnerabilities in the Bronto platform or its HTTP API rather than
in this client (report those to **security@bronto.io** directly), and findings
in third-party dependencies with no exploitable path through this SDK — please
report those upstream, though we welcome a heads-up.

## Credential handling

This SDK holds API keys and bearer tokens, so reports in that area are
particularly welcome. By design a credential must never reach an exception
message, a `repr()`, or a log line, and a client is either client-bound or
per-request with no fallback between the two. A case where a credential leaks
into any of those, or where the two credential modes mix, is a vulnerability
even without a further exploit.

## Verifying a release

Release artifacts are attached to each [GitHub
Release](https://github.com/bronto-community/bronto-sdk-python/releases). The
wheel and sdist are built by the `release.yml` workflow from the tagged commit;
no artifact is uploaded by hand.
