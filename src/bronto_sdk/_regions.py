"""Regional URL registry."""

from __future__ import annotations

import re

from ._errors import BrontoConfigError

# A hint for error messages only, never an allow-list. New regions must
# work without shipping a new SDK version.
KNOWN_REGIONS: tuple[str, ...] = ("eu", "us")

_REGION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def validate_region(region: str) -> str:
    """Validate a region slug, raising if it could smuggle a host.

    Args:
        region: The region slug to validate (e.g. ``"eu"``, ``"us"``).

    Returns:
        The region unchanged when it matches the slug pattern.

    Raises:
        BrontoConfigError: If ``region`` contains any character that could move
            the host off ``bronto.io`` (a slash, ``@``, dot, colon, whitespace,
            or uppercase).
    """
    if not _REGION_PATTERN.match(region):
        raise BrontoConfigError(
            f"Invalid region {region!r}. A region must be a slug like 'eu' or "
            "'us' (lowercase letters, digits, and dashes, starting with a "
            "letter or digit). Use base_url for a custom or non-standard "
            "endpoint."
        )
    return region


def rest_base_url(region: str) -> str:
    """Return the REST API base URL for a region.

    Args:
        region: The region slug.

    Returns:
        ``https://api.{region}.bronto.io``.
    """
    return f"https://api.{validate_region(region)}.bronto.io"


def mcp_url(region: str) -> str:
    """Return the MCP endpoint URL for a region.

    Args:
        region: The region slug.

    Returns:
        ``https://mcp.{region}.bronto.io/mcp``.
    """
    return f"https://mcp.{validate_region(region)}.bronto.io/mcp"


def ingest_base_url(region: str) -> str:
    """Return the ingestion base URL for a region.

    Args:
        region: The region slug.

    Returns:
        ``https://ingestion.{region}.bronto.io``.
    """
    return f"https://ingestion.{validate_region(region)}.bronto.io"
