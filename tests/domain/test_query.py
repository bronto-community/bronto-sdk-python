"""Tests for query literal and attribute escaping.

Bronto follows SQL quoting: single quotes wrap a string literal (embedded ``'``
doubled), double quotes wrap an attribute (identifier) reference (embedded ``"``
doubled), and backslash escaping is not a thing. Escaping is opt-in here, so
these tests also pin that the raw helpers leave a backslash untouched — proving
the SDK is not silently rewriting a caller's clause.
"""

import pytest

from bronto_sdk.domain import (
    escape_double_quotes,
    escape_single_quotes,
    quote_attribute,
    quote_value,
    wildcard_pattern,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("plain", "plain"),
        ("O'Brien", "O''Brien"),
        ("''", "''''"),
        ("a'b'c", "a''b''c"),
        ("", ""),
    ],
)
def test_escape_single_quotes_doubles_only_single_quotes(value, expected):
    assert escape_single_quotes(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('my "odd" field', 'my ""odd"" field'),
        ('""', '""""'),
        ("no quotes", "no quotes"),
    ],
)
def test_escape_double_quotes_doubles_only_double_quotes(value, expected):
    assert escape_double_quotes(value) == expected


def test_quote_value_wraps_a_string_literal_in_single_quotes():
    assert quote_value("O'Brien") == "'O''Brien'"
    assert quote_value("plain") == "'plain'"
    assert quote_value("") == "''"


def test_quote_attribute_wraps_an_identifier_in_double_quotes():
    assert quote_attribute("my field") == '"my field"'
    assert quote_attribute('my "odd" field') == '"my ""odd"" field"'
    assert quote_attribute("") == '""'


def test_backslashes_pass_through_untouched():
    # The engine does not support backslash escaping, so a backslash is an
    # ordinary character. Doubling it would corrupt the caller's value.
    assert escape_single_quotes(r"a\b") == r"a\b"
    assert quote_value(r"C:\path") == r"'C:\path'"
    assert quote_attribute(r"a\b") == r'"a\b"'


def test_injection_payload_is_neutralised_by_quoting():
    # A classic SQL-injection-shaped value: once quoted, the embedded quotes are
    # doubled, so the payload cannot break out of the literal.
    payload = "' OR '1'='1"
    assert quote_value(payload) == "''' OR ''1''=''1'"


@pytest.mark.parametrize(
    ("fragments", "expected"),
    [
        (["foo"], "%foo%"),
        (["foo", "bar"], "%foo%bar%"),
        ([], "%"),
    ],
)
def test_wildcard_pattern_joins_with_percent(fragments, expected):
    assert wildcard_pattern(fragments) == expected


def test_wildcard_pattern_escaping_is_opt_in():
    # Default: fragments pass through verbatim, quotes and all.
    assert wildcard_pattern(["O'Brien"]) == "%O'Brien%"
    # Opt-in: single quotes in each fragment are doubled before joining.
    assert wildcard_pattern(["O'Brien"], escape=True) == "%O''Brien%"
