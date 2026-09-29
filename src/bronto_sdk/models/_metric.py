"""Models for ``GET /metrics/definitions/{id}``."""

from __future__ import annotations

from ._common import ReadModel
from ._monitor import MonitorFormula, MonitorQuery


class MetricDefinition(ReadModel):
    """The metric definition behind a monitor.

    Attributes:
        id: The definition's identifier — a monitor's ``metric_id``.
        queries: The queries the metric is computed from. Each names its
            datasets by ``from`` ids or a ``from_expr``.
        formulas: Expressions combining ``queries``.
    """

    id: str | None = None
    queries: list[MonitorQuery] | None = None
    formulas: list[MonitorFormula] | None = None
