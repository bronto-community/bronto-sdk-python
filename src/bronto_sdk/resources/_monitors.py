"""Typed access to the monitor read operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .._request_options import RequestOptions
from ..models import Monitor, MonitorEventsResponse, MonitorsResponse

if TYPE_CHECKING:
    from .._async_client import AsyncBrontoClient
    from .._client import BrontoClient

MONITORS_PATH = "monitors"


def _monitor_path(monitor_id: str) -> str:
    """Build the path for one monitor, quoting the id into a single segment.

    Args:
        monitor_id: The monitor's identifier.

    Returns:
        The request path, e.g. ``"monitors/m-1"``.

    Raises:
        ValueError: When ``monitor_id`` is empty — an empty segment would
            silently address the monitor collection instead.
    """
    if not monitor_id:
        raise ValueError("monitor_id must be a non-empty string")
    return f"monitors/{quote(monitor_id, safe='')}"


def _monitor_events_path(monitor_id: str) -> str:
    """Build the path for one monitor's event history.

    Args:
        monitor_id: The monitor's identifier.

    Returns:
        The request path, e.g. ``"monitors/m-1/events"``.

    Raises:
        ValueError: When ``monitor_id`` is empty.
    """
    return f"{_monitor_path(monitor_id)}/events"


def _events_params(from_ts: int | None, to_ts: int | None) -> dict[str, Any] | None:
    """Assemble the event-history query parameters, dropping unset bounds.

    Args:
        from_ts: Window start in epoch milliseconds, or ``None``.
        to_ts: Window end in epoch milliseconds, or ``None``.

    Returns:
        The query parameters, or ``None`` when neither bound is set.
    """
    params: dict[str, Any] = {}
    if from_ts is not None:
        params["from_ts"] = from_ts
    if to_ts is not None:
        params["to_ts"] = to_ts
    return params or None


class MonitorsResource:
    """The typed monitor surface, reached as ``client.monitors``."""

    def __init__(self, client: BrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.BrontoClient`.
        """
        self._client = client

    def list(self, *, options: RequestOptions | None = None) -> MonitorsResponse:
        """List every monitor.

        The endpoint takes no filters and has no pagination, so this returns
        the whole set in one call.

        Args:
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MonitorsResponse`.

        Raises:
            BrontoAPIError: On any non-2xx response, including a 403 when the
                credential may not view monitors.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.get(MONITORS_PATH, options=options)
        return MonitorsResponse.model_validate(raw)

    def retrieve(
        self, monitor_id: str, *, options: RequestOptions | None = None
    ) -> Monitor:
        """Fetch one monitor by id.

        Args:
            monitor_id: The monitor's identifier.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.Monitor`.

        Raises:
            ValueError: When ``monitor_id`` is empty.
            BrontoAPIError: On any non-2xx response, including a 404 for an
                unknown monitor.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.get(_monitor_path(monitor_id), options=options)
        return Monitor.model_validate(raw)

    def events(
        self,
        monitor_id: str,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
        options: RequestOptions | None = None,
    ) -> MonitorEventsResponse:
        """Fetch a monitor's state-change history.

        Args:
            monitor_id: The monitor's identifier.
            from_ts: Optional window start in epoch milliseconds.
            to_ts: Optional window end in epoch milliseconds.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MonitorEventsResponse`.

        Raises:
            ValueError: When ``monitor_id`` is empty.
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.get(
            _monitor_events_path(monitor_id),
            params=_events_params(from_ts, to_ts),
            options=options,
        )
        return MonitorEventsResponse.model_validate(raw)


class AsyncMonitorsResource:
    """The typed monitor surface, reached as ``client.monitors``."""

    def __init__(self, client: AsyncBrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.AsyncBrontoClient`.
        """
        self._client = client

    async def list(self, *, options: RequestOptions | None = None) -> MonitorsResponse:
        """List every monitor.

        The endpoint takes no filters and has no pagination, so this returns
        the whole set in one call.

        Args:
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MonitorsResponse`.

        Raises:
            BrontoAPIError: On any non-2xx response, including a 403 when the
                credential may not view monitors.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.get(MONITORS_PATH, options=options)
        return MonitorsResponse.model_validate(raw)

    async def retrieve(
        self, monitor_id: str, *, options: RequestOptions | None = None
    ) -> Monitor:
        """Fetch one monitor by id.

        Args:
            monitor_id: The monitor's identifier.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.Monitor`.

        Raises:
            ValueError: When ``monitor_id`` is empty.
            BrontoAPIError: On any non-2xx response, including a 404 for an
                unknown monitor.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.get(_monitor_path(monitor_id), options=options)
        return Monitor.model_validate(raw)

    async def events(
        self,
        monitor_id: str,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
        options: RequestOptions | None = None,
    ) -> MonitorEventsResponse:
        """Fetch a monitor's state-change history.

        Args:
            monitor_id: The monitor's identifier.
            from_ts: Optional window start in epoch milliseconds.
            to_ts: Optional window end in epoch milliseconds.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MonitorEventsResponse`.

        Raises:
            ValueError: When ``monitor_id`` is empty.
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.get(
            _monitor_events_path(monitor_id),
            params=_events_params(from_ts, to_ts),
            options=options,
        )
        return MonitorEventsResponse.model_validate(raw)
