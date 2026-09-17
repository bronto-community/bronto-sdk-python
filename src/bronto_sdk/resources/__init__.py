"""Typed access to the REST operations this SDK covers.

Reach a resource through its client accessor — ``client.search``,
``client.monitors``, ``client.datasets`` — rather than constructing one
directly. The classes are re-exported here only so a caller can name the type
in an annotation.

Anything the SDK does not cover stays reachable through the ``client.get`` /
``client.post`` escape hatches, so a consumer is never blocked on a release.
"""

from __future__ import annotations

from ._datasets import AsyncDatasetsResource, DatasetsResource
from ._monitors import AsyncMonitorsResource, MonitorsResource
from ._search import AsyncSearchResource, SearchResource

__all__ = [
    "AsyncDatasetsResource",
    "AsyncMonitorsResource",
    "AsyncSearchResource",
    "DatasetsResource",
    "MonitorsResource",
    "SearchResource",
]
