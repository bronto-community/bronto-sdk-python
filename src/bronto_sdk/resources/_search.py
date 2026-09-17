"""Typed access to ``POST /search``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._request_options import RequestOptions
from ..models import SearchRequest, SearchResponse

if TYPE_CHECKING:
    from .._async_client import AsyncBrontoClient
    from .._client import BrontoClient

SEARCH_PATH = "/search"


def _search_payload(request: SearchRequest | dict[str, Any]) -> dict[str, Any]:
    """Render a search request into the JSON body the API expects.

    Args:
        request: A :class:`bronto_sdk.models.SearchRequest`, or a dict in the
            wire shape.

    Returns:
        The request body, with every unset field omitted so the server applies
        its own defaults.

    Raises:
        pydantic.ValidationError: When a supplied dict is not a valid search.
    """
    return SearchRequest.model_validate(request).to_payload()


class SearchResource:
    """The typed ``POST /search`` surface, reached as ``client.search``."""

    def __init__(self, client: BrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.BrontoClient`.
        """
        self._client = client

    def run(
        self,
        request: SearchRequest | dict[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> SearchResponse:
        """Run a search.

        Args:
            request: The search to run, as a
                :class:`bronto_sdk.models.SearchRequest` or an equivalent dict.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.SearchResponse`.

        Raises:
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = self._client.post(
            SEARCH_PATH, json=_search_payload(request), options=options
        )
        return SearchResponse.model_validate(raw)


class AsyncSearchResource:
    """The typed ``POST /search`` surface, reached as ``client.search``."""

    def __init__(self, client: AsyncBrontoClient) -> None:
        """Bind the resource to the client that performs its requests.

        Args:
            client: The owning :class:`bronto_sdk.AsyncBrontoClient`.
        """
        self._client = client

    async def run(
        self,
        request: SearchRequest | dict[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> SearchResponse:
        """Run a search.

        Args:
            request: The search to run, as a
                :class:`bronto_sdk.models.SearchRequest` or an equivalent dict.
            options: Optional per-request overrides.

        Returns:
            The parsed :class:`bronto_sdk.models.SearchResponse`.

        Raises:
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        raw = await self._client.post(
            SEARCH_PATH, json=_search_payload(request), options=options
        )
        return SearchResponse.model_validate(raw)
