"""Models for ``POST /search``."""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._common import ReadModel


class SearchLink(ReadModel):
    """A navigation link on a search response or an individual result.

    Attributes:
        rel: What the link points at. Known values are ``next``, ``prev``,
            ``first`` and ``status`` on a response, and ``context`` on an event.
        href: The URL to follow.
    """

    rel: str | None = None
    href: str | None = None


class HistogramBucket(ReadModel):
    """One bucket of a value-distribution histogram.

    Attributes:
        name: The bucket's label, e.g. ``"lower than 10"``.
        low_bound: The bucket's inclusive lower bound.
        high_bound: The bucket's upper bound.
        value: The number of events in the bucket. Declared ``number`` in the
            spec but typed ``int`` here — it is a count.
    """

    name: str | None = None
    low_bound: float | None = None
    high_bound: float | None = None
    value: int | None = None


class Histogram(ReadModel):
    """A value distribution over a group or a time slice.

    Attributes:
        min: The smallest value recorded, when available.
        max: The largest value recorded, when available.
        buckets: The distribution's buckets.
    """

    min: float | None = None
    max: float | None = None
    buckets: list[HistogramBucket] | None = None


class TimeSlice(ReadModel):
    """One bucket of a timeseries.

    Attributes:
        timestamp: Start of the slice in epoch milliseconds.
        count: Number of matching events in the slice.
        value: The statistical function's value for the slice.
        quantiles: Distribution summary keyed by ``min``, ``p25`` … ``max``.
            Often present but empty.
        histogram: Distribution as a histogram, for histogram metrics.
    """

    timestamp: int | None = Field(
        default=None, validation_alias="@timestamp", serialization_alias="@timestamp"
    )
    count: int | None = None
    value: float | None = None
    quantiles: dict[str, float] | None = None
    histogram: Histogram | None = None


class QueryExplain(ReadModel):
    """Query-execution diagnostics.

    Attributes:
        execution_time_millis: Query execution time in milliseconds.
        bytes_searched: Bytes scanned to answer the query
        matching_events: How many events matched.
    """

    execution_time_millis: str | None = Field(
        default=None,
        validation_alias="Execution time (millis)",
        serialization_alias="Execution time (millis)",
    )
    bytes_searched: str | None = Field(
        default=None,
        validation_alias="Bytes searched",
        serialization_alias="Bytes searched",
    )
    matching_events: str | None = Field(
        default=None,
        validation_alias="Matching events",
        serialization_alias="Matching events",
    )


class EventMetadata(ReadModel):
    """Metadata on an ``events`` entry.

    Attributes:
        service_id: Id of the dataset the event came from.
        timestamp: Ingest time in epoch milliseconds.
        sequence: The event's sequence number, routinely above 2**53.
        context: URL returning the events surrounding this one.
    """

    service_id: str | None = None
    timestamp: int | None = None
    sequence: int | None = None
    context: str | None = None


class Event(ReadModel):
    """One event from the ``events`` array.

    Attributes:
        raw: The log message as received. Present only when ``select`` named
            ``@raw``.
        time: Human-readable ingest time, formatted
            ``"2024-05-27 23:26:34.331 UTC"`` — not ISO 8601.
        status: Severity of the event.
            Documented values are ``info``, ``warn`` and ``error``.
        message_kvs: Projected fields parsed from the log message itself.
            A key an event lacks arrives as ``""`` rather than absent: the API
            pads every event in a response to one common key set.
        attributes: Projected details attached to the event at ingestion —
            resource attributes, environment settings, and custom attributes
            defined by the user.
        metadata: Ingest metadata for the event.
        links: Related-resource links.
    """

    raw: str | None = Field(
        default=None, validation_alias="@raw", serialization_alias="@raw"
    )
    time: str | None = Field(
        default=None, validation_alias="@time", serialization_alias="@time"
    )
    status: str | None = Field(
        default=None, validation_alias="@status", serialization_alias="@status"
    )
    message_kvs: dict[str, Any] | None = None
    attributes: dict[str, Any] | None = None
    metadata: EventMetadata | None = None
    links: list[SearchLink] | None = None


class GroupSeriesItem(ReadModel):
    """One group-by row with its timeseries.

    Attributes:
        key: The group-by key this series is for, e.g. ``"hostname"``.
        name: The group's name.
        count: How many events fell in this group across the window.
        stat: The statistical function applied, e.g. ``"max(latency_ms)"``.
        value: The function's value over the whole window.
        histogram: Distribution as a histogram, for histogram metrics.
        quantiles: Distribution summary keyed by ``min``, ``p25`` … ``max``.
        timeseries: The group's buckets.
        groups_series: Sub-group series, one level per additional group-by key.
        delta: Period-over-period comparison figures.
    """

    key: str | None = None
    name: str | None = None
    count: int | None = None
    stat: str | None = None
    value: float | None = None
    histogram: Histogram | None = None
    quantiles: dict[str, float] | None = None
    timeseries: list[TimeSlice] | None = None
    groups_series: list[GroupSeriesItem] | None = None
    delta: dict[str, Any] | None = None


class QueryMetadata(ReadModel):
    """Metadata describing the query that produced a response.

    Attributes:
        select: The columns the query selected, in request order.
        correlation_id: Identifier for this query, for support and tracing.
    """

    select: list[str] | None = None
    correlation_id: str | None = None


class Pagination(ReadModel):
    """Where to fetch the next page of results.

    Attributes:
        next_page_url: URL for the next page, absent when there is none.
    """

    next_page_url: str | None = None


class SearchTotals(ReadModel):
    """Whole-window totals.

    Attributes:
        count: Total matching events.
        timeseries: The window's buckets, for the first bucketed metric.
        total_groups: How many groups matched.
        retrieved_groups: How many groups were actually returned.
    """

    count: int | float | None = None
    timeseries: list[TimeSlice] | None = None
    total_groups: float | None = None
    retrieved_groups: float | None = None


class SearchResponse(ReadModel):
    """A ``POST /search`` response.

    Attributes:
        explain: Query-execution diagnostics.
        events: The matching events, each carrying the caller's ``select``
            projection. The array to read whatever the projection was.
        groups_series: Group-by rows with their timeseries. Empty for an
            ungrouped query, which reports through ``totals`` instead.
        metadata: The query's own metadata, including its correlation id.
        totals: Whole-window totals. Where an ungrouped aggregate's result
            lands, since ``groups_series`` is empty for one.
        pagination: Next-page URL, when there is a next page.
        links: Navigation links. Carries the ``status`` link that an
            ``async_enabled`` query is polled through.
        is_exact: Whether the result is exact rather than estimated.
    """

    explain: QueryExplain | None = None
    events: list[Event] | None = None
    groups_series: list[GroupSeriesItem] | None = None
    metadata: QueryMetadata | None = None
    totals: SearchTotals | None = None
    pagination: Pagination | None = None
    links: list[SearchLink] | None = None
    is_exact: bool | None = None


class SearchRequest(BaseModel):
    """A ``POST /search`` request body.

    Serialise with :meth:`to_payload`, never with a bare ``model_dump()`` —
    ``from_`` has to go on the wire as ``from``.

    Attributes:
        select: Columns or aggregate functions to return. Required and
            non-empty, e.g. ``["count(*)"]`` or ``["*", "@raw"]``.
        from_: Dataset ids to search, sent as ``from``. Mutually exclusive with
            ``from_expr``.
        from_expr: Dataset selector expression, e.g.
            ``"collection = 'prod'"``. Mutually exclusive with ``from_``.
        time_range: Relative window, e.g. ``"Last 1 hour"``. Mutually exclusive
            with ``from_ts``/``to_ts``.
        from_ts: Window start in epoch milliseconds. Must be given together
            with ``to_ts``.
        to_ts: Window end in epoch milliseconds. Must be given together with
            ``from_ts``.
        where: Filter predicate. Passed through verbatim — the SDK never
            escapes a caller's clause; see :mod:`bronto_sdk.domain.query`.
        groups: Group-by keys. Named ``groups``, not ``group_by``.
        limit: Maximum events, or maximum groups for an aggregate query.
        num_of_slices: Number of timeseries buckets.
        from_sequence: Sequence number to resume from, for sub-millisecond
            precision alongside ``from_ts``.
        most_recent_first: Whether to return the newest events first.
        explain_only: Return only the ``explain`` diagnostics, running no query.
        async_enabled: Run asynchronously, returning a ``status`` link to poll.
        order_by: Sort expression, e.g. ``"response_time_ms DESC"``.
        pagination_token: Token from a previous response's ``links``. When set,
            every filter except ``per_page`` is ignored.
        per_page: Page size, used with ``pagination_token``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    select: list[str] = Field(min_length=1)
    from_: list[str] | None = Field(
        default=None, validation_alias="from", serialization_alias="from"
    )
    from_expr: str | None = None
    time_range: str | None = None
    from_ts: int | None = None
    to_ts: int | None = None
    where: str | None = None
    groups: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=10000)
    num_of_slices: int | None = None
    from_sequence: int | None = None
    most_recent_first: bool | None = None
    explain_only: bool | None = None
    async_enabled: bool | None = None
    order_by: str | None = None
    pagination_token: str | None = None
    per_page: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def _check_exclusive_parameters(self) -> Self:
        """Reject the two parameter combinations the API forbids.

        Returns:
            The validated model.

        Raises:
            ValueError: If both dataset selectors are set, if ``time_range``
                is combined with an absolute bound, or if only one of
                ``from_ts``/``to_ts`` is given.
        """
        if self.from_ is not None and self.from_expr is not None:
            raise ValueError(
                "'from_' and 'from_expr' are mutually exclusive; set one or neither"
            )
        if self.time_range is not None and (
            self.from_ts is not None or self.to_ts is not None
        ):
            raise ValueError(
                "'time_range' is mutually exclusive with 'from_ts'/'to_ts'; "
                "use a relative window or an absolute one, not both"
            )
        if (self.from_ts is None) != (self.to_ts is None):
            raise ValueError(
                "'from_ts' and 'to_ts' must be supplied together; "
                "a lone bound is a half-specified window"
            )
        return self

    def to_payload(self) -> dict[str, Any]:
        """Render the request as the JSON body the API expects.

        Dumps by alias so ``from_`` is emitted as ``from``, and drops every
        unset field so the server applies its own defaults.

        Returns:
            The request body, ready to hand to ``client.post("/search", ...)``.
        """
        return self.model_dump(by_alias=True, exclude_none=True)
