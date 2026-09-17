"""Bronto's standard error envelope, as a model."""

from __future__ import annotations

from ._common import ReadModel


class ErrorResponse(ReadModel):
    """The ``{code, type, correlation_id, details}`` envelope Bronto returns.

    Attributes:
        code: The HTTP status code, between 400 and 599.
        type: The HTTP reason phrase, e.g. ``"Not Found"``.
        correlation_id: Bronto's request correlation id. The single most useful
            field when raising a support ticket.
        details: The human-readable error description.
    """

    code: int | None = None
    type: str | None = None
    correlation_id: str | None = None
    details: str | None = None
