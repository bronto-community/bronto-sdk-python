"""Fan out concurrent searches through one async client.

``AsyncBrontoClient`` mirrors ``BrontoClient`` method-for-method — same names,
``async def`` bodies. Its ``max_concurrency`` semaphore bounds in-flight
requests, so a fan-out like this one cannot stampede the API gateway however
wide the gather gets.

Run with ``BRONTO_API_KEY`` and ``BRONTO_REGION`` set:

    uv run python examples/async_search.py
"""

from __future__ import annotations

import asyncio

from bronto_sdk import AsyncBrontoClient
from bronto_sdk.models import SearchRequest, SearchResponse

WINDOWS = ["last 15 minutes", "last 1 hour", "last 6 hours", "last 1 day"]


async def count_errors(client: AsyncBrontoClient, window: str) -> SearchResponse:
    """Count error events over one window.

    Args:
        client: The async client to search through.
        window: A natural-language window the query engine understands.

    Returns:
        The parsed search response.
    """
    return await client.search.run(
        SearchRequest(
            select=["count(*)"],
            from_expr="*",
            time_range=window,
            where="$status='error'",
        )
    )


async def main() -> None:
    """Run every window's count concurrently and print the totals."""
    # from_env() takes no overrides, so the cap is its default of 20.
    async with AsyncBrontoClient.from_env() as client:
        responses = await asyncio.gather(
            *(count_errors(client, window) for window in WINDOWS)
        )

    for window, response in zip(WINDOWS, responses, strict=True):
        print(f"{window:>16}: {response.totals}")


if __name__ == "__main__":
    asyncio.run(main())
