"""Fetch one monitor and print the playbook an agent would act on.

Run with ``BRONTO_API_KEY`` and ``BRONTO_REGION`` set:

    uv run python examples/get_monitor.py <monitor-id>
"""

from __future__ import annotations

import sys

from bronto_sdk import BrontoClient, BrontoNotFoundError


def main(monitor_id: str) -> None:
    """Print a monitor's name, status and configured playbook."""
    with BrontoClient.from_env() as client:
        try:
            monitor = client.monitors.retrieve(monitor_id)
        except BrontoNotFoundError as exc:
            # correlation_id is what a support ticket needs, so surface it.
            print(f"no such monitor: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    print(f"{monitor.id}  {monitor.name}  [{monitor.status}]")
    print(monitor.ai_report_instructions or "(no playbook configured)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: get_monitor.py <monitor-id>")
    main(sys.argv[1])
