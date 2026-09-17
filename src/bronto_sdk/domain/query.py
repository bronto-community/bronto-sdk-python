"""Helpers for embedding literals and attribute names in Bronto queries.

The Bronto query language follows SQL quoting conventions. **Single quotes wrap
a string literal** — ``'error'`` is the string ``error`` — and an embedded
single quote is escaped by doubling it (``'` `` becomes ``''``). **Double quotes
wrap an attribute (identifier) reference** — ``"my field"`` names the attribute
``my field`` — and an embedded double quote is likewise escaped by doubling it.
Backslash escaping is **not** supported by the engine, so a backslash is an
ordinary character and is left untouched here.

**Escaping is opt-in, never automatic.** The SDK's default contract is that a
caller supplies already-valid query text; nothing in this module (or the
resource layer) silently rewrites a caller's clause.
"""

from __future__ import annotations

from collections.abc import Iterable

# Bronto's single-character wildcard for LIKE-style matching, joined between
# fragments by wildcard_pattern.
WILDCARD = "%"


def escape_single_quotes(value: str) -> str:
    """Double every single quote in ``value`` for a string literal.

    This escapes the *contents* of a ``'...'`` string literal; it does not add
    the surrounding quotes. Use :func:`quote_value` when you want the wrapped,
    ready-to-embed form.

    Args:
        value: The raw text destined for a ``'...'`` string literal.

    Returns:
        ``value`` with each ``'`` replaced by ``''``.
    """
    return value.replace("'", "''")


def escape_double_quotes(value: str) -> str:
    """Double every double quote in ``name`` for an attribute reference.

    Double quotes wrap an attribute (identifier) name in the query language, not
    a string literal. This escapes the *contents* of a ``"..."`` attribute
    reference; it does not add the surrounding quotes. Use
    :func:`quote_attribute` for the wrapped form.

    Args:
        value: The raw attribute name destined for a ``"..."`` reference.

    Returns:
        ``value`` with each ``"`` replaced by ``""``.
    """
    return value.replace('"', '""')


def quote_value(value: str) -> str:
    """Return ``value`` as a safe single-quoted string literal.

    Doubles embedded single quotes and wraps the result in single quotes, so a
    value like ``O'Brien`` becomes ``'O''Brien'``.

    Args:
        value: The raw string literal to quote.

    Returns:
        The escaped, single-quoted string literal.
    """
    return f"'{escape_single_quotes(value)}'"


def quote_attribute(name: str) -> str:
    """Return ``name`` as a safe double-quoted attribute reference.`.

    Args:
        name: The raw attribute name to quote.

    Returns:
        The escaped, double-quoted attribute reference.
    """
    return f'"{escape_double_quotes(name)}"'


def wildcard_pattern(fragments: Iterable[str], *, escape: bool = False) -> str:
    """Join ``fragments`` with Bronto's ``%`` wildcard into a LIKE pattern.

    Args:
        fragments: The literal fragments to match between wildcards.
        escape: When ``True``, double single quotes in each fragment first.

    Returns:
        A ``%``-delimited wildcard pattern.
    """
    parts = [escape_single_quotes(f) if escape else f for f in fragments]
    return WILDCARD + WILDCARD.join([*parts, ""])
    """Join ``fragments`` with Bronto's ``%`` wildcard into a LIKE pattern.

    The result has a leading and trailing wildcard and a wildcard between every
    fragment, so ``["foo", "bar"]`` becomes ``%foo%bar%``. The pattern is
    returned unquoted; wrap it with :func:`quote_value` (or escape each fragment
    via ``escape=True``) before embedding it in a clause.

    Escaping stays opt-in to match the module contract: pass ``escape=True``
    in which case each fragment's single quotes are doubled before joining.

    Args:
        fragments: The literal fragments to match between wildcards.
        escape: When ``True``, double single quotes in each fragment first.

    Returns:
        A ``%``-delimited wildcard pattern.
    """
    parts = [escape_single_quotes(f) if escape else f for f in fragments]
    return WILDCARD + WILDCARD.join([*parts, ""])
