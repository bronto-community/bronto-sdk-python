"""The synchronous Bronto client — a thin I/O shell over ``httpx.Client``.

Every request-shaping decision lives in the pure helpers of
:mod:`bronto_sdk._client_config` and :mod:`bronto_sdk._transport`; this module
only performs the actual HTTP call, so it stays a mirror of
:class:`bronto_sdk._async_client.AsyncBrontoClient`.
"""

from __future__ import annotations

from functools import cached_property
from types import TracebackType
from typing import Any

import httpx

from ._client_config import (
    client_default_options,
    prepare_request,
    read_env_config,
    resolve_base_url,
    wrap_transport_error,
)
from ._request_options import RequestOptions, client_credential
from ._transport import parse_response
from .resources._datasets import DatasetsResource
from .resources._monitors import MonitorsResource
from .resources._search import SearchResource


class BrontoClient:
    """A synchronous client for the Bronto REST API.

    The client is either *client-bound* (constructed with ``api_key`` or
    ``bearer_token``; every call uses it) or *credential-less* (constructed with
    neither; every call must supply a credential via ``options``). The mode is
    fixed at construction — see the two-mode rule in
    :mod:`bronto_sdk._request_options`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        region: str | None = None,
        *,
        bearer_token: str | None = None,
        timeout: float = 30.0,
        base_url: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Construct a client.

        Args:
            api_key: A Bronto API key to bind to every call. Omit for a
                credential-less client.
            region: The region slug (e.g. ``"eu"``); resolved to the REST base
                URL. Ignored when ``base_url`` is given.
            bearer_token: A JWT bearer token to bind to every call. Wins over
                ``api_key``. Omit for a credential-less client.
            timeout: The default per-request timeout in seconds.
            base_url: An explicit base URL that overrides ``region`` — for
                testing or a non-standard deployment. Trusted and used verbatim.
            http_client: An existing ``httpx.Client`` to reuse. When given, the
                SDK will not close it.

        Raises:
            BrontoConfigError: When neither ``region`` nor ``base_url`` resolves
                an endpoint, or the region slug is invalid.
        """
        self._base_url = resolve_base_url(region=region, base_url=base_url)
        self._bound = client_credential(api_key=api_key, bearer_token=bearer_token)
        self._defaults = client_default_options(timeout=timeout)
        self._http = http_client or httpx.Client()
        self._owns_http_client = http_client is None

    @classmethod
    def from_env(cls) -> BrontoClient:
        """Build a client from ``BRONTO_API_KEY`` and ``BRONTO_REGION``.

        ``BRONTO_BASE_URL`` is honoured when set and wins over ``BRONTO_REGION``.

        Returns:
            A client-bound :class:`BrontoClient`.

        Raises:
            BrontoConfigError: Naming the first missing environment variable.
        """
        env = read_env_config()
        return cls(api_key=env.api_key, region=env.region, base_url=env.base_url)

    @cached_property
    def search(self) -> SearchResource:
        """The typed ``POST /search`` surface."""
        return SearchResource(self)

    @cached_property
    def monitors(self) -> MonitorsResource:
        """The typed monitor surface."""
        return MonitorsResource(self)

    @cached_property
    def datasets(self) -> DatasetsResource:
        """The typed dataset surface."""
        return DatasetsResource(self)

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> dict[str, object]:
        """Send a ``GET`` request and return the parsed JSON object.

        Args:
            path: The request path, absolute-style (``"/search"``) or bare
                (``"monitors/m-1"``).
            params: Optional query-string parameters.
            options: Optional per-request overrides.

        Returns:
            The decoded JSON response object.

        Raises:
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        return self._request(
            "GET", path, params=params, json_body=None, options=options
        )

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> dict[str, object]:
        """Send a ``POST`` request and return the parsed JSON object.

        Args:
            path: The request path, absolute-style or bare.
            json: Optional JSON request body.
            params: Optional query-string parameters.
            options: Optional per-request overrides.

        Returns:
            The decoded JSON response object.

        Raises:
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        return self._request(
            "POST", path, params=params, json_body=json, options=options
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
        options: RequestOptions | None,
    ) -> dict[str, object]:
        """Perform the shared per-call flow around a single ``httpx`` request.

        Args:
            method: The HTTP method.
            path: The request path.
            params: Optional query-string parameters.
            json_body: Optional JSON request body.
            options: Optional per-request overrides.

        Returns:
            The decoded JSON response object.

        Raises:
            BrontoAPIError: On any non-2xx response.
            BrontoConnectionError: On a transport-level failure.
            BrontoConfigError: On a credential resolution error.
        """
        prepared = prepare_request(
            bound=self._bound,
            defaults=self._defaults,
            base_url=self._base_url,
            path=path,
            options=options,
        )
        timeout = (
            prepared.timeout
            if prepared.timeout is not None
            else httpx.USE_CLIENT_DEFAULT
        )
        try:
            response = self._http.request(
                method,
                prepared.url,
                params=params,
                json=json_body,
                headers=prepared.headers,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc) from exc
        return parse_response(response.status_code, response.headers, response.text)

    def close(self) -> None:
        """Close the underlying HTTP client, unless it was caller-supplied."""
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> BrontoClient:
        """Enter the context manager, returning the client."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the client on context-manager exit."""
        self.close()
