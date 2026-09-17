"""Time conversions and natural-language range parsing for Bronto searches.

Two shapes of time input reach the Bronto search API: absolute epoch-millisecond
bounds and relative/natural phrases like ``"last 30 minutes"`` or
``"2 hours ago"``.

All epoch values are integer milliseconds. Nothing here is ever typed ``float``:
a Bronto epoch-ms or sequence number can exceed 2**53, where a float silently
loses precision.
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, datetime, timedelta

_MS_SECOND = 1000
_MS_MINUTE = 60 * _MS_SECOND
_MS_HOUR = 60 * _MS_MINUTE
_MS_DAY = 24 * _MS_HOUR
_MS_WEEK = 7 * _MS_DAY
_MS_MONTH = 30 * _MS_DAY
_MS_YEAR = 365 * _MS_DAY

_UNIT_MS: dict[str, int] = {
    "millis": 1,
    "milli": 1,
    "ms": 1,
    "millisecond": 1,
    "milliseconds": 1,
    "second": _MS_SECOND,
    "seconds": _MS_SECOND,
    "sec": _MS_SECOND,
    "secs": _MS_SECOND,
    "s": _MS_SECOND,
    "minute": _MS_MINUTE,
    "minutes": _MS_MINUTE,
    "min": _MS_MINUTE,
    "mins": _MS_MINUTE,
    "m": _MS_MINUTE,
    "hour": _MS_HOUR,
    "hours": _MS_HOUR,
    "h": _MS_HOUR,
    "day": _MS_DAY,
    "days": _MS_DAY,
    "d": _MS_DAY,
    "week": _MS_WEEK,
    "weeks": _MS_WEEK,
    "w": _MS_WEEK,
    "month": _MS_MONTH,
    "months": _MS_MONTH,
    "year": _MS_YEAR,
    "years": _MS_YEAR,
    "y": _MS_YEAR,
}

_WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_UNIT_ALTERNATION = (
    r"milliseconds?|millis?|ms|seconds?|secs?|s|minutes?|mins?|m|"
    r"hours?|h|days?|d|weeks?|w|months?|years?|y"
)
_COUNT_ALTERNATION = r"\d+|" + "|".join(_WORD_NUMBERS)

_LAST_PATTERN = re.compile(
    rf"last\s*({_COUNT_ALTERNATION})?\s*({_UNIT_ALTERNATION})",
    re.IGNORECASE,
)

_AGO_PATTERN = re.compile(
    rf"^\s*({_COUNT_ALTERNATION})?\s*({_UNIT_ALTERNATION})\s*(ago)?\s*$",
    re.IGNORECASE,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_ONE_MS = timedelta(milliseconds=1)


def iso_to_ms(timestamp: str) -> int:
    """Convert an ISO-8601 timestamp to unix-epoch milliseconds.

    A timestamp with no timezone is assumed to be UTC.

    Args:
        timestamp: An ISO-8601 timestamp (e.g. ``"2026-07-07T12:00:00"``).

    Returns:
        The instant as integer milliseconds since the unix epoch.
    """
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return _to_ms(parsed)


def ms_to_iso(ms: int) -> str:
    """Convert unix-epoch milliseconds to an ISO-8601 UTC timestamp.

    The millisecond value is applied via an integer ``timedelta`` rather than a
    float division, so an epoch beyond 2**53 milliseconds does not lose
    precision.

    Args:
        ms: Milliseconds since the unix epoch.

    Returns:
        An ISO-8601 timestamp in UTC (offset ``+00:00``).
    """
    return (_EPOCH + timedelta(milliseconds=ms)).isoformat()


def parse_time_range(
    natural: str,
    ref: datetime | None = None,
    *,
    full_duration: bool = False,
) -> tuple[int, int]:
    """Resolve a natural-language range to absolute epoch-millisecond bounds.

    Understood inputs are calendar phrases (``"today"``, ``"yesterday"``,
    ``"this week"``, ``"previous month"``, ``"this quarter"``, ...),
    the ``"last N <unit>"`` form, and the ``"N <unit> [ago]"`` form.
    Counts may be digits or the words ``one``..``ten``; an omitted count means one.
    An empty string yields ``(0, ref)``.

    Args:
        natural: The phrase to parse.
        ref: The reference instant relative phrases are measured from; defaults
            to the current UTC time. A naive datetime is assumed to be UTC.
        full_duration: For a calendar phrase covering the current period
            (``"today"``, ``"this week"``, ``"this month"``, ``"this year"``,
            ``"this quarter"``), when ``True`` the upper bound is the end of the
            whole period; when ``False`` it is ``ref``.

    Returns:
        A ``(from_ms, to_ms)`` tuple of integer epoch milliseconds, with
        ``from_ms <= to_ms``.

    Raises:
        ValueError: If ``natural`` matches no understood form.
    """
    ref = _normalise_ref(ref)
    ref_ms = _to_ms(ref)

    if not natural.strip():
        return (0, ref_ms)

    phrase = natural.strip().lower()
    calendar_range = _parse_calendar_phrase(phrase, ref, ref_ms, full_duration)
    if calendar_range is not None:
        return calendar_range

    duration = _match_relative_duration(natural)
    if duration is not None:
        return (ref_ms - duration, ref_ms)

    raise ValueError(f"could not parse time range: {natural!r}")


def parse_window(natural: str, ref: datetime | None = None) -> int:
    """Parse a Bronto window phrase into a millisecond duration.

    Args:
        natural: The window phrase (e.g. ``"last 30 minutes"``, ``"5 mins"``,
            ``"2 hours ago"``).
        ref: The reference instant; defaults to the current UTC time. Only
            affects calendar phrases whose span depends on the reference.

    Returns:
        The window length in milliseconds.

    Raises:
        ValueError: If ``natural`` matches no understood form.
    """
    from_ms, to_ms = parse_time_range(natural, ref)
    return to_ms - from_ms


def _normalise_ref(ref: datetime | None) -> datetime:
    """Return ``ref`` as a UTC-aware datetime, defaulting to now."""
    if ref is None:
        return datetime.now(UTC)
    if ref.tzinfo is None:
        return ref.replace(tzinfo=UTC)
    return ref.astimezone(UTC)


def _to_ms(dt: datetime) -> int:
    """Return integer epoch milliseconds for a timezone-aware datetime."""
    delta = dt - _EPOCH
    return (
        delta.days * _MS_DAY + delta.seconds * _MS_SECOND + delta.microseconds // 1000
    )


def _start_of_day(dt: datetime) -> datetime:
    """Truncate ``dt`` to the start of its UTC day."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _add_days(dt: datetime, days: int) -> datetime:
    """Return ``dt`` shifted by ``days`` days."""
    return dt + timedelta(days=days)


def _add_months(dt: datetime, months: int) -> datetime:
    """Shift ``dt`` by ``months``, clamping the day to the target month length."""
    index = dt.month - 1 + months
    year = dt.year + index // 12
    month = index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _count_value(count_text: str | None) -> int:
    """Resolve a count group (digits, a spelled-out word, or absent) to an int."""
    if count_text is None:
        return 1
    return _WORD_NUMBERS.get(count_text.lower(), 0) or int(count_text)


def _match_relative_duration(natural: str) -> int | None:
    """Return the ms duration for a "last N unit" / "N unit ago" phrase.

    Returns ``None`` when the phrase matches neither form so the caller can
    raise a single, uniform error.
    """
    match = _LAST_PATTERN.search(natural) or _AGO_PATTERN.match(natural)
    if match is None:
        return None
    count = _count_value(match.group(1))
    return _UNIT_MS[match.group(2).lower()] * count


def _parse_calendar_phrase(
    phrase: str,
    ref: datetime,
    ref_ms: int,
    full_duration: bool,
) -> tuple[int, int] | None:
    """Resolve a named calendar phrase, or ``None`` if it is not one."""
    start_today = _start_of_day(ref)

    if phrase == "today":
        end = _to_ms(_add_days(start_today, 1) - _ONE_MS) if full_duration else ref_ms
        return (_to_ms(start_today), end)
    if phrase == "yesterday":
        start = _add_days(start_today, -1)
        return (_to_ms(start), _to_ms(_add_days(start, 1) - _ONE_MS))
    if phrase == "day before yesterday":
        start = _add_days(start_today, -2)
        return (_to_ms(start), _to_ms(_add_days(start, 1) - _ONE_MS))
    if phrase == "this week":
        start = _add_days(start_today, -ref.weekday())
        end = _to_ms(_add_days(start, 7) - _ONE_MS) if full_duration else ref_ms
        return (_to_ms(start), end)
    if phrase == "previous week":
        start = _add_days(start_today, -ref.weekday() - 7)
        return (_to_ms(start), _to_ms(_add_days(start, 7) - _ONE_MS))
    if phrase == "this day last week":
        start = _add_days(start_today, -7)
        return (_to_ms(start), _to_ms(_add_days(start, 1) - _ONE_MS))
    if phrase == "this month":
        start = start_today.replace(day=1)
        end = _to_ms(_add_months(start, 1) - _ONE_MS) if full_duration else ref_ms
        return (_to_ms(start), end)
    if phrase == "previous month":
        start = _add_months(start_today.replace(day=1), -1)
        return (_to_ms(start), _to_ms(_add_months(start, 1) - _ONE_MS))
    if phrase == "this year":
        start = start_today.replace(month=1, day=1)
        end = _to_ms(_add_months(start, 12) - _ONE_MS) if full_duration else ref_ms
        return (_to_ms(start), end)
    if phrase == "previous year":
        start = start_today.replace(month=1, day=1).replace(year=start_today.year - 1)
        return (_to_ms(start), _to_ms(_add_months(start, 12) - _ONE_MS))
    if phrase == "this quarter":
        return _quarter(ref, ref_ms, 0, full_duration)
    if phrase == "previous quarter":
        return _quarter(ref, ref_ms, -1, full_duration)
    if phrase == "this quarter last year":
        return _quarter(ref, ref_ms, -4, full_duration)
    return None


def _quarter(
    ref: datetime,
    ref_ms: int,
    offset: int,
    full_duration: bool,
) -> tuple[int, int]:
    """Resolve a quarter range ``offset`` quarters from ``ref``'s quarter."""
    quarter_start_month = ref.month - ((ref.month - 1) % 3)
    start = _start_of_day(ref).replace(month=quarter_start_month, day=1)
    start = _add_months(start, offset * 3)
    if offset == 0 and not full_duration:
        return (_to_ms(start), ref_ms)
    return (_to_ms(start), _to_ms(_add_months(start, 3) - _ONE_MS))
