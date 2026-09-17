"""Models for ``GET /datasets``.

Note the REST and MCP APIs name a dataset's fields differently: REST returns
``id`` and ``dataset``, the MCP tools return ``log_id`` and ``name``. These
models cover the **REST** shape only. :func:`bronto_sdk.domain.project_dataset`
is the helper that spans both and it stays dict-based on purpose.
"""

from __future__ import annotations

from typing import Any

from ._common import ReadModel, ResourceMetadata


class Dataset(ReadModel):
    """A Bronto dataset — one named stream within a collection.

    Attributes:
        id: The dataset's identifier. Called ``log_id`` by the MCP tools.
        collection: The collection the dataset belongs to, e.g. ``"demo"``.
        dataset: The dataset's name within the collection, e.g.
            ``"firewall"``. Called ``name`` by the MCP tools.
        is_system_generated: Whether Bronto created the dataset itself.
        tags: Free-form key/value labels.
        parser_id: The parser applied to incoming events. The spec declares
            ``format: uuid``, but live responses return ``""`` for an unparsed
            dataset, so this stays a plain string.
        metadata: Creation and modification audit block. Its
            ``last_heartbeat_at`` is the usual signal of whether a dataset is
            still receiving data.
    """

    id: str
    collection: str
    dataset: str
    is_system_generated: bool | None = None
    tags: dict[str, Any] | None = None
    parser_id: str | None = None
    metadata: ResourceMetadata | None = None


class DatasetsResponse(ReadModel):
    """A ``GET /datasets`` response.

    Attributes:
        datasets: The matching datasets. Empty when nothing matched.
    """

    datasets: list[Dataset] | None = None
