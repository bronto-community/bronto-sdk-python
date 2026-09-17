"""Tests for time conversion and natural-language range parsing."""

from datetime import UTC, datetime

import pytest

from bronto_sdk.domain import (
    iso_to_ms,
    ms_to_iso,
    parse_time_range,
    parse_window,
)

# 2026-07-07T12:00:00Z, a Tuesday. Used as the reference instant everywhere.
REF = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)
REF_MS = 1_783_425_600_000

DAY_MS = 86_400_000


def test_ref_constant_is_self_consistent():
    assert iso_to_ms("2026-07-07T12:00:00") == REF_MS


def test_iso_to_ms_honours_an_explicit_offset():
    # 12:00 at +02:00 is 10:00 UTC, two hours earlier than the naive reading.
    assert iso_to_ms("2026-07-07T12:00:00+02:00") == REF_MS - 2 * 3_600_000


def test_ms_to_iso_round_trips():
    assert ms_to_iso(REF_MS) == "2026-07-07T12:00:00+00:00"


def test_sub_second_ms_round_trips_without_float_corruption():
    # ms_to_iso applies the value via an integer timedelta, not ms / 1000.0.
    # 1783425600001 / 1000 is not exactly representable as a float, so a float
    # round-trip could drop the trailing millisecond; the integer path must not.
    ms = 1_783_425_600_001
    assert iso_to_ms(ms_to_iso(ms)) == ms


@pytest.mark.parametrize(
    ("phrase", "seconds"),
    [
        # The exact phrases the consumers used with dateparser.
        ("last 30 minutes", 30 * 60),
        ("5 mins", 5 * 60),
        ("2 hours ago", 2 * 3600),
        ("1 day", 86400),
        ("1 month", 30 * 86400),
        # Broader unit coverage.
        ("90 seconds", 90),
        ("last 1 hour", 3600),
        ("3 days", 3 * 86400),
        ("2 weeks", 2 * 7 * 86400),
        ("1 year", 365 * 86400),
        # Shorthand units.
        ("last 15m", 15 * 60),
        ("3d", 3 * 86400),
        ("last 1w", 7 * 86400),
    ],
)
def test_relative_phrases_resolve_to_a_window_ending_at_ref(phrase, seconds):
    from_ms, to_ms = parse_time_range(phrase, REF)
    assert to_ms == REF_MS
    assert from_ms == REF_MS - seconds * 1000


@pytest.mark.parametrize(
    ("phrase", "expected_ms"),
    [
        ("last hour", 3600 * 1000),  # omitted count means one
        ("minute", 60 * 1000),  # bare unit, "ago" form
        ("last two days", 2 * 86400 * 1000),  # spelled-out count
        ("ten mins", 10 * 60 * 1000),
    ],
)
def test_omitted_and_worded_counts(phrase, expected_ms):
    assert parse_window(phrase, REF) == expected_ms


def test_parse_window_is_the_duration_projection():
    assert parse_window("last 30 minutes", REF) == 30 * 60 * 1000


@pytest.mark.parametrize(
    ("phrase", "expected_ms"),
    [
        ("500 ms", 500),
        ("500 millis", 500),
        ("1 millisecond", 1),
        ("last 250 ms", 250),
    ],
)
def test_millisecond_units_keep_sub_second_precision(phrase, expected_ms):
    assert parse_window(phrase, REF) == expected_ms


@pytest.mark.parametrize("blank", ["", "  "])
def test_empty_input_yields_zero_to_ref(blank):
    assert parse_time_range(blank, REF) == (0, REF_MS)


@pytest.mark.parametrize("garbage", ["garbage", "5x", "m5", "next tuesday", "soon"])
def test_unparseable_input_raises_value_error(garbage):
    with pytest.raises(ValueError):
        parse_time_range(garbage, REF)


def test_today_bounds():
    start = iso_to_ms("2026-07-07T00:00:00")
    assert parse_time_range("today", REF) == (start, REF_MS)
    assert parse_time_range("today", REF, full_duration=True) == (
        start,
        iso_to_ms("2026-07-07T23:59:59.999"),
    )


def test_yesterday_bounds():
    assert parse_time_range("yesterday", REF) == (
        iso_to_ms("2026-07-06T00:00:00"),
        iso_to_ms("2026-07-06T23:59:59.999"),
    )


def test_day_before_yesterday_bounds():
    assert parse_time_range("day before yesterday", REF) == (
        iso_to_ms("2026-07-05T00:00:00"),
        iso_to_ms("2026-07-05T23:59:59.999"),
    )


def test_this_week_starts_monday():
    # 2026-07-07 is a Tuesday, so this week's Monday is 2026-07-06.
    start = iso_to_ms("2026-07-06T00:00:00")
    assert parse_time_range("this week", REF) == (start, REF_MS)
    assert parse_time_range("this week", REF, full_duration=True) == (
        start,
        iso_to_ms("2026-07-12T23:59:59.999"),
    )


def test_previous_week_bounds():
    assert parse_time_range("previous week", REF) == (
        iso_to_ms("2026-06-29T00:00:00"),
        iso_to_ms("2026-07-05T23:59:59.999"),
    )


def test_this_day_last_week_bounds():
    assert parse_time_range("this day last week", REF) == (
        iso_to_ms("2026-06-30T00:00:00"),
        iso_to_ms("2026-06-30T23:59:59.999"),
    )


def test_this_month_bounds():
    start = iso_to_ms("2026-07-01T00:00:00")
    assert parse_time_range("this month", REF) == (start, REF_MS)
    assert parse_time_range("this month", REF, full_duration=True) == (
        start,
        iso_to_ms("2026-07-31T23:59:59.999"),
    )


def test_previous_month_bounds():
    assert parse_time_range("previous month", REF) == (
        iso_to_ms("2026-06-01T00:00:00"),
        iso_to_ms("2026-06-30T23:59:59.999"),
    )


def test_this_year_bounds():
    start = iso_to_ms("2026-01-01T00:00:00")
    assert parse_time_range("this year", REF) == (start, REF_MS)
    assert parse_time_range("this year", REF, full_duration=True) == (
        start,
        iso_to_ms("2026-12-31T23:59:59.999"),
    )


def test_previous_year_bounds():
    assert parse_time_range("previous year", REF) == (
        iso_to_ms("2025-01-01T00:00:00"),
        iso_to_ms("2025-12-31T23:59:59.999"),
    )


def test_this_quarter_bounds():
    # July is in Q3, which starts on 1 July.
    start = iso_to_ms("2026-07-01T00:00:00")
    assert parse_time_range("this quarter", REF) == (start, REF_MS)
    assert parse_time_range("this quarter", REF, full_duration=True) == (
        start,
        iso_to_ms("2026-09-30T23:59:59.999"),
    )


def test_previous_quarter_bounds():
    assert parse_time_range("previous quarter", REF) == (
        iso_to_ms("2026-04-01T00:00:00"),
        iso_to_ms("2026-06-30T23:59:59.999"),
    )


def test_this_quarter_last_year_bounds():
    assert parse_time_range("this quarter last year", REF) == (
        iso_to_ms("2025-07-01T00:00:00"),
        iso_to_ms("2025-09-30T23:59:59.999"),
    )


def test_phrases_are_case_insensitive_and_trimmed():
    assert parse_time_range("  LAST 30 Minutes  ", REF) == parse_time_range(
        "last 30 minutes", REF
    )
    assert parse_time_range("TODAY", REF) == parse_time_range("today", REF)


def test_naive_ref_is_treated_as_utc():
    naive = datetime(2026, 7, 7, 12, 0, 0)
    assert parse_time_range("last 1 hour", naive) == parse_time_range(
        "last 1 hour", REF
    )


def test_default_ref_uses_now():
    # Without an explicit ref the window still ends "about now"; assert the
    # duration is exact even though the absolute bounds float with the clock.
    from_ms, to_ms = parse_time_range("last 1 hour")
    assert to_ms - from_ms == 3600 * 1000
