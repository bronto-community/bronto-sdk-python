"""Smoke tests proving the harness and the version wiring work end to end."""

import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest

import bronto_sdk

# The release gates are POSIX shell run by the Linux release job. The Windows
# matrix leg has no shell to run them, and skipping is honest: nothing about
# the gate is platform-specific, so proving it on the platform that runs it is
# the whole of the claim.
requires_posix_shell = pytest.mark.skipif(
    sys.platform == "win32", reason="version-check.sh is POSIX shell"
)


def test_version_is_importable():
    """The package re-exports VERSION with no side effects on import."""
    assert bronto_sdk.VERSION == "0.1.0"
    assert "VERSION" in bronto_sdk.__all__
    assert all(hasattr(bronto_sdk, name) for name in bronto_sdk.__all__)


def test_version_matches_version_file(repo_root: Path):
    """`bronto_sdk.VERSION` agrees with the VERSION file at the repo root."""
    assert bronto_sdk.VERSION == (repo_root / "VERSION").read_text().strip()


def test_version_matches_installed_metadata():
    """`bronto_sdk.VERSION` agrees with the distribution metadata.

    This is the leg that catches a partial `just update-version` run: bumping
    `_version.py` and `VERSION` while leaving `pyproject.toml` behind would ship
    a wheel whose metadata disagrees with the module, which is exactly the
    three-way drift the single-source-of-truth rule exists to prevent.
    """
    assert bronto_sdk.VERSION == version("bronto-sdk")


def _run_version_check(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run scripts/version-check.sh with the given arguments."""
    return subprocess.run(
        [str(repo_root / "scripts" / "version-check.sh"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@requires_posix_shell
def test_version_check_accepts_the_matching_tag(repo_root: Path):
    """The release gate passes when the tag names the recorded version."""
    result = _run_version_check(repo_root, "--self-test", "v0.1.0")
    assert result.returncode == 0, result.stderr


@requires_posix_shell
def test_version_check_rejects_a_mismatching_tag(repo_root: Path):
    """The release gate fails when the tag disagrees with the version files.

    A regression test with a specific history: the `--self-test` branch used to
    end in `set --`, which clears *every* positional argument, so the tag that
    followed it was discarded and this comparison never ran. CI accepted a
    `v0.1.0rc1` tag against a 0.1.0 tree and only the changelog gate downstream
    stopped the release. The gate could not go red, which is the one property
    this repository asks of a gate.
    """
    result = _run_version_check(repo_root, "--self-test", "v9.9.9")
    assert result.returncode == 1
    assert "does not match the recorded version" in result.stderr


@requires_posix_shell
def test_version_check_without_a_tag_checks_only_the_files(repo_root: Path):
    """A workflow_dispatch rehearsal passes an empty tag and must still pass."""
    assert _run_version_check(repo_root, "--self-test", "").returncode == 0
    assert _run_version_check(repo_root, "--self-test").returncode == 0
