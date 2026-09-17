"""Dataset domain knowledge."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def project_dataset(dataset: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a dataset object to the ``log_id``/``name``/``collection`` triple.

    Reads both API shapes: the name is taken from ``name`` (MCP) falling back to
    ``dataset`` (REST), and the id from ``log_id`` (MCP) falling back to ``id``
    (REST).

    Args:
        dataset: A dataset object from either the REST or MCP API.

    Returns:
        A dict with exactly ``log_id``, ``name``, and ``collection`` keys.
    """
    return {
        "log_id": dataset.get("log_id", dataset.get("id")),
        "name": dataset.get("name", dataset.get("dataset")),
        "collection": dataset.get("collection"),
    }
