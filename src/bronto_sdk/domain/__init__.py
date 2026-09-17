"""Pure Bronto domain helpers.

These modules encode Bronto domain knowledge — how to parse a window phrase,
how to escape a query literal, which collections hold logs — as plain functions
with no dependency on the client or on any network access. They are safe to
import and call in isolation.
"""

from __future__ import annotations

from .datasets import project_dataset
from .query import (
    WILDCARD,
    escape_double_quotes,
    escape_single_quotes,
    quote_attribute,
    quote_value,
    wildcard_pattern,
)
from .time_range import (
    iso_to_ms,
    ms_to_iso,
    parse_time_range,
    parse_window,
)

__all__ = [
    "WILDCARD",
    "escape_double_quotes",
    "escape_single_quotes",
    "iso_to_ms",
    "ms_to_iso",
    "parse_time_range",
    "parse_window",
    "project_dataset",
    "quote_attribute",
    "quote_value",
    "wildcard_pattern",
]
