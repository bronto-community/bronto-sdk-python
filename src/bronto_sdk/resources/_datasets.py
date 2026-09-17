"""Typed access to ``GET /datasets``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._request_options import RequestOptions
from ..models import DatasetsResponse

if TYPE_CHECKING:
    from .._async_client import AsyncBrontoClient
    from .._client import BrontoClient

DATASETS_PATH = "/datasets"


def _list_params(
    from_: list[str] | None, from_expr: str | None
) -> dict[str, Any] | None:
    """Assemble the dataset-listing query parameters.

    The list goes out under the wire key ``from``, which is a Python keyword —
    the same rename :meth:`bronto_sdk.models.SearchRequest.to_payload` performs
    for the search body.

    Args:
        from_: Dataset ids to filter by, or ``None``.
        from_expr: A dataset selector expression, or ``None``.

    Returns:
        The query parameters, or ``None`` when neither selector is set — in
        which case the API returns every dataset.

    Raises:
        ValueError: When both selectors are supplied. The API accepts at most
            one, and guessing which the caller meant is not the SDK's call.
    """
    if from_ is not None and from_expr is not None:
        raise ValueError(
            "'from_' and 'from_expr' are mutually exclusive; the API accepts at "
            "most one dataset selector"
        )
    if from_ is not None:
        return {"from": from_}
    if from_expr is not None:
        return {"from_expr": from_expr}
    return None


class DatasetsResource:
    """The typed dataset surface, reached as ``client.datasets``."""

    def __init__(self, client: BrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.BrontoClient`.
        """
        self._client = client

    def list(
        self,
        *,
        from_: list[str] | None = None,
        from_expr: str | None = None,
        options: RequestOptions | None = None,
    ) -> DatasetsResponse:
        """List the datasets.

        Args:
            from_: Dataset ids to filter by. Mutually exclusive with
                ``from_expr``; omit both to list everything.
            from_expr: A dataset selector expression, e.g.
                ``"collection = 'prod'"``. Mutually exclusive with ``from_``.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.DatasetsResponse`. A selector
            that matches nothing yields an empty ``datasets`` list, not a 404.

        Raises:
            ValueError: When both selectors are supplied.
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.get(
            DATASETS_PATH, params=_list_params(from_, from_expr), options=options
        )
        return DatasetsResponse.model_validate(raw)


class AsyncDatasetsResource:
    """The typed dataset surface, reached as ``client.datasets``."""

    def __init__(self, client: AsyncBrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.AsyncBrontoClient`.
        """
        self._client = client

    async def list(
        self,
        *,
        from_: list[str] | None = None,
        from_expr: str | None = None,
        options: RequestOptions | None = None,
    ) -> DatasetsResponse:
        """List the datasets.

        Args:
            from_: Dataset ids to filter by. Mutually exclusive with
                ``from_expr``; omit both to list everything.
            from_expr: A dataset selector expression, e.g.
                ``"collection = 'prod'"``. Mutually exclusive with ``from_``.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.DatasetsResponse`. A selector
            that matches nothing yields an empty ``datasets`` list, not a 404.

        Raises:
            ValueError: When both selectors are supplied.
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.get(
            DATASETS_PATH, params=_list_params(from_, from_expr), options=options
        )
        return DatasetsResponse.model_validate(raw)
