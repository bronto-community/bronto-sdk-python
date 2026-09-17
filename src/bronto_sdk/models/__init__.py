"""Typed shapes for the REST subset the SDK covers."""

from __future__ import annotations

from ._common import Identity, ResourceMetadata
from ._dataset import Dataset, DatasetsResponse
from ._error import ErrorResponse
from ._monitor import (
    Monitor,
    MonitorAction,
    MonitorAggregation,
    MonitoredGroup,
    MonitorEvent,
    MonitorEventsResponse,
    MonitorFormula,
    MonitorGroupHistory,
    MonitorGroupStatusChange,
    MonitorQuery,
    MonitorsResponse,
    MonitorTemplateRef,
)
from ._search import (
    Event,
    EventMetadata,
    GroupSeriesItem,
    Histogram,
    HistogramBucket,
    Pagination,
    QueryExplain,
    QueryMetadata,
    SearchLink,
    SearchRequest,
    SearchResponse,
    SearchTotals,
    TimeSlice,
)

__all__ = [
    "Dataset",
    "DatasetsResponse",
    "ErrorResponse",
    "Event",
    "EventMetadata",
    "GroupSeriesItem",
    "Histogram",
    "HistogramBucket",
    "Identity",
    "Monitor",
    "MonitorAction",
    "MonitorAggregation",
    "MonitorEvent",
    "MonitorEventsResponse",
    "MonitorFormula",
    "MonitorGroupHistory",
    "MonitorGroupStatusChange",
    "MonitorQuery",
    "MonitorTemplateRef",
    "MonitoredGroup",
    "MonitorsResponse",
    "Pagination",
    "QueryExplain",
    "QueryMetadata",
    "ResourceMetadata",
    "SearchLink",
    "SearchRequest",
    "SearchResponse",
    "SearchTotals",
    "TimeSlice",
]
