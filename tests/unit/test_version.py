"""Smoke tests proving the harness and the version wiring work end to end."""

from importlib.metadata import version
from pathlib import Path

import bronto_sdk


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
