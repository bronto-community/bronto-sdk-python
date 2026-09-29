"""Typed access to ``GET /metrics/definitions/{id}``."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from .._request_options import RequestOptions
from ..models import MetricDefinition

if TYPE_CHECKING:
    from .._async_client import AsyncBrontoClient
    from .._client import BrontoClient


def _definition_path(metric_id: str) -> str:
    """Build the path for one metric definition, quoting the id into one segment.

    Args:
        metric_id: The definition's identifier, e.g. a monitor's ``metric_id``.

    Returns:
        The request path, e.g. ``"metrics/definitions/md-1"``.

    Raises:
        ValueError: When ``metric_id`` is empty — an empty segment would
            silently address the definition collection instead.
    """
    if not metric_id:
        raise ValueError("metric_id must be a non-empty string")
    return f"metrics/definitions/{quote(metric_id, safe='')}"


class MetricsResource:
    """The typed metric-definition surface, reached as ``client.metrics``."""

    def __init__(self, client: BrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.BrontoClient`.
        """
        self._client = client

    def retrieve_definition(
        self, metric_id: str, *, options: RequestOptions | None = None
    ) -> MetricDefinition:
        """Fetch one metric definition — where a monitor's queries live.

        Args:
            metric_id: The definition's identifier; a monitor's ``metric_id``.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MetricDefinition`.

        Raises:
            ValueError: When ``metric_id`` is empty.
            BrontoAPIError: On any non-2xx response, including a 404 for an
                unknown definition.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.get(_definition_path(metric_id), options=options)
        return MetricDefinition.model_validate(raw)


class AsyncMetricsResource:
    """The typed metric-definition surface, reached as ``client.metrics``."""

    def __init__(self, client: AsyncBrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.AsyncBrontoClient`.
        """
        self._client = client

    async def retrieve_definition(
        self, metric_id: str, *, options: RequestOptions | None = None
    ) -> MetricDefinition:
        """Fetch one metric definition — where a monitor's queries live.

        Args:
            metric_id: The definition's identifier; a monitor's ``metric_id``.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.MetricDefinition`.

        Raises:
            ValueError: When ``metric_id`` is empty.
            BrontoAPIError: On any non-2xx response, including a 404 for an
                unknown definition.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.get(_definition_path(metric_id), options=options)
        return MetricDefinition.model_validate(raw)
