"""Models for the monitor read operations.

Covers ``GET /monitors``, ``GET /monitors/{id}`` and
``GET /monitors/{id}/events``.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from ._common import ReadModel, ResourceMetadata


class MonitorAction(ReadModel):
    """Something the monitor does when it changes state.

    Attributes:
        type: The action's kind. Known values are ``EMAIL`` and
            ``INTEGRATION``.
        email: Recipient address, for an ``EMAIL`` action.
        integration_id: Target integration, for an ``INTEGRATION`` action.
    """

    type: str | None = None
    email: str | None = None
    integration_id: str | None = None


class MonitoredGroup(ReadModel):
    """The current state of one group a grouped monitor watches.

    Attributes:
        group_id: The group's composite key, e.g. ``"region:EU,host:100"``.
        groups: The group's key/value pairs.
        status: The group's status. Known values are ``OK``, ``NO_DATA``,
            ``ALERT`` and ``WARN``.
    """

    group_id: str | None = None
    groups: dict[str, Any] | None = None
    status: str | None = None


class MonitorTemplateRef(ReadModel):
    """A reference to the template a monitor was instantiated from.

    Attributes:
        id: The template's identifier.
        arguments: Arguments bound when the monitor was instantiated.
    """

    id: str | None = None
    arguments: dict[str, Any] | None = None


class MonitorAggregation(ReadModel):
    """How a monitor query aggregates over time and across series.

    Attributes:
        time: The aggregation applied over the time axis, e.g. ``"count"``.
        reduce_to: How series are reduced together, e.g. ``"avg"``.
    """

    time: str | None = None
    reduce_to: str | None = None


class MonitorFormula(ReadModel):
    """A named expression combining a monitor's queries.

    Attributes:
        name: The formula's name, referenced by the monitor's threshold.
        expression: The expression, e.g. ``"errors / total * 100"``.
    """

    name: str | None = None
    expression: str | None = None


class MonitorQuery(ReadModel):
    """One query backing a monitor.

    Attributes:
        id: The query's identifier. Present on live responses though the
            spec's ``QueryDefinition`` does not declare it.
        name: The query's name.
        select: Columns or aggregate functions, e.g. ``["COUNT(*)"]``.
        from_: Dataset ids the query reads, under the wire key ``from``.
        from_expr: Dataset selector expression. Empty string when unused.
        where: The query's filter predicate.
        groups: Group-by keys.
        aggregation: How the query aggregates.
    """

    id: str | None = None
    name: str | None = None
    select: list[str] | None = None
    from_: list[str] | None = Field(
        default=None, validation_alias="from", serialization_alias="from"
    )
    from_expr: str | None = None
    where: str | None = None
    groups: list[str] | None = None
    aggregation: list[MonitorAggregation] | None = None


class Monitor(ReadModel):
    """A Bronto monitor.

    Attributes:
        id: The monitor's identifier.
        name: The monitor's display name.
        description: Free-text description.
        comparison_operator: How ``threshold`` is compared. Known values are
            ``BELOW``, ``BELOW_OR_EQUAL``, ``ABOVE``, ``ABOVE_OR_EQUAL``,
            ``EQUAL``, ``NOT_EQUAL`` and ``OUTSIDE``.
        threshold: The alerting threshold. Genuinely fractional, so ``float``.
        warning_threshold: The warning threshold, when one is set.
        window: The evaluation window as a phrase, e.g. ``"Last 20 minutes"``.
            Parse it with :func:`bronto_sdk.domain.parse_window`.
        actions: What the monitor does when it changes state.
        status: The monitor's current status. Known values are ``OK``,
            ``NO_DATA``, ``ALERT`` and ``WARN``.
        monitored_groups: Per-group state, for a grouped monitor.
        no_data_status: The status to report when no data arrives.
        muted_until: Mute expiry in epoch milliseconds; ``-1`` means forever.
        notify_once: Whether to notify only on the first trigger.
        group_retention: How long a group is remembered, in milliseconds.
        last_trigger_ts: Last trigger time in epoch milliseconds.
        aux: Free-form auxiliary settings, e.g. ``{"query_mode": "raw"}``.
        monitor_type: The monitor's kind. Known values are ``PATTERN``,
            ``USAGE``, ``CHANGE_DETECTION`` and ``ANOMALY_DETECTION``.
        compare_to: Comparison offset for a ``CHANGE_DETECTION`` monitor,
            e.g. ``"2 hours ago"``.
        change_type: How change is measured. Known values are ``DIFFERENCE``
            and ``PERCENTAGE``.
        evaluation_window: Baseline window for anomaly detection.
        anomaly_algorithm: The anomaly algorithm. Known value ``MEDIAN_MAD``.
        ai_report_enabled: Whether an AI report is generated on trigger.
        ai_report_instructions: The configured playbook text, when one is set.
        metric_id: The backing metric definition's identifier.
        template: The template this monitor was instantiated from.
        metadata: Creation and modification audit block.
        queries: The queries backing the monitor. Declared on the spec's
            create-request schema but not on its ``Monitor`` read schema; on
            some deployments they live on the backing metric definition
            instead, which v0.1 does not cover — hence optional.
        formulas: Expressions combining ``queries``. Same provenance.
        tags: Free-form key/value labels. Same provenance.
    """

    id: str
    name: str
    description: str | None = None
    comparison_operator: str | None = None
    threshold: float | None = None
    warning_threshold: float | None = None
    window: str | None = None
    actions: list[MonitorAction] | None = None
    status: str | None = None
    monitored_groups: list[MonitoredGroup] | None = None
    no_data_status: str | None = None
    muted_until: int | None = None
    notify_once: bool | None = None
    group_retention: int | None = None
    last_trigger_ts: int | None = None
    aux: dict[str, Any] | None = None
    monitor_type: str | None = None
    compare_to: str | None = None
    change_type: str | None = None
    evaluation_window: str | None = None
    anomaly_algorithm: str | None = None
    ai_report_enabled: bool | None = None
    ai_report_instructions: str | None = None
    metric_id: str | None = None
    template: MonitorTemplateRef | None = None
    metadata: ResourceMetadata | None = None
    queries: list[MonitorQuery] | None = None
    formulas: list[MonitorFormula] | None = None
    tags: dict[str, Any] | None = None


class MonitorEvent(ReadModel):
    """One state change in a monitor's history.

    Attributes:
        monitor_id: The monitor this event belongs to.
        time: When the change happened, in epoch milliseconds. Declared
            ``number`` in the spec; typed ``int`` because a float rounds
            values above 2**53.
        monitor_status: The status after the change. Known values are ``OK``,
            ``ALERT``, ``WARN`` and ``NO_DATA``.
        previous_status: The status before the change.
        message: A short summary, e.g. ``"The monitor has been resolved"``.
    """

    monitor_id: str | None = None
    time: int | None = None
    monitor_status: str | None = None
    previous_status: str | None = None
    message: str | None = None


class MonitorGroupStatusChange(ReadModel):
    """One state change for a single group of a grouped monitor.

    Attributes:
        time: When the change happened, in epoch milliseconds. Declared
            ``number`` in the spec; typed ``int`` for the same reason as
            :attr:`MonitorEvent.time`.
        status: The status after the change. Known values are ``OK``,
            ``NO_DATA``, ``ALERT`` and ``WARN``.
    """

    time: int | None = None
    status: str | None = None


class MonitorGroupHistory(ReadModel):
    """One group's state-change history.

    Attributes:
        monitor_id: The monitor this history belongs to.
        group_id: The group's key, e.g. ``"host:ip-10-0-0-1"``.
        history: The group's state changes.
    """

    monitor_id: str | None = None
    group_id: str | None = None
    history: list[MonitorGroupStatusChange] | None = None


class MonitorEventsResponse(ReadModel):
    """A ``GET /monitors/{id}/events`` response.

    The endpoint takes only ``from_ts``/``to_ts`` and has no count limit and no
    pagination, so a wide window returns everything.

    Attributes:
        monitor_events: The monitor's state changes, newest first.
        groups_history: Per-group state-change history, for a grouped monitor.
    """

    monitor_events: list[MonitorEvent] | None = None
    groups_history: list[MonitorGroupHistory] | None = None


class MonitorsResponse(ReadModel):
    """A ``GET /monitors`` response.

    Attributes:
        monitors: The configured monitors. Empty when there are none.
    """

    monitors: list[Monitor] | None = None
