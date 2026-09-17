"""Run a log search, escaping an untrusted value into the where clause.

The escaping is the point of this example. ``quote_value`` is called explicitly
at the call site, because the SDK never rewrites a clause you supply.

Run with ``BRONTO_API_KEY`` and ``BRONTO_REGION`` set:

    uv run python examples/search_logs.py
"""

from __future__ import annotations

from bronto_sdk import BrontoClient
from bronto_sdk.domain import parse_window, quote_value
from bronto_sdk.models import SearchRequest

SERVICE = "service name with whitespace and ' char"


def main() -> None:
    """Search the last 30 minutes for one service's error lines."""
    window = "last 30 minutes"
    print(f"window {window!r} is {parse_window(window)} ms")

    request = SearchRequest(
        select=["*", "@raw"],
        from_expr="*",
        time_range=window,
        where=f"$status='error' AND $service={quote_value(SERVICE)}",
        most_recent_first=True,
        limit=20,
    )
    print(f"where: {request.where}")

    with BrontoClient.from_env() as client:
        response = client.search.run(request)

    for event in response.events or []:
        print(event.time, event.raw)


if __name__ == "__main__":
    main()
