"""Resolve the Bronto MCP endpoint and its auth header.

Run with ``BRONTO_API_KEY`` and ``BRONTO_REGION`` set:

    uv run python examples/mcp_endpoint.py
"""

from __future__ import annotations

import os

from bronto_sdk import mcp


def main() -> None:
    """Print the MCP endpoint and header for the configured region."""
    region = os.environ.get("BRONTO_REGION", "eu")
    api_key = os.environ.get("BRONTO_API_KEY", "")

    print(f"region endpoint: {mcp.url(region)}")

    if not api_key:
        print("set BRONTO_API_KEY to see the auth header")
        return

    headers = mcp.auth_headers(api_key=api_key)
    # The header dict goes onto the httpx client the MCP transport is built on
    # (the streamable-HTTP client takes headers that way, not as an argument).
    print(f"auth header key: {next(iter(headers))}")


if __name__ == "__main__":
    main()
