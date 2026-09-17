"""Python SDK for the Bronto observability platform.

Importing this package has no side effects: it configures no logging, reads no
environment variables, opens no connections, and holds no global mutable state.
A client instance is the only entry point.

Only the names re-exported here (and the documented `domain`, `models`,
`resources` and `mcp` subpackages) are public API; everything in a module
prefixed with `_` is an implementation detail and may change without a major
version bump.
"""

from ._async_client import AsyncBrontoClient
from ._client import BrontoClient
from ._errors import (
    BrontoAPIError,
    BrontoAuthenticationError,
    BrontoBadRequestError,
    BrontoConfigError,
    BrontoConnectionError,
    BrontoError,
    BrontoNotFoundError,
    BrontoPermissionError,
    BrontoRateLimitError,
    BrontoServerError,
)
from ._regions import (
    KNOWN_REGIONS,
    ingest_base_url,
    mcp_url,
    rest_base_url,
    validate_region,
)
from ._request_options import RequestOptions
from ._version import VERSION

__all__ = [
    "KNOWN_REGIONS",
    "VERSION",
    "AsyncBrontoClient",
    "BrontoAPIError",
    "BrontoAuthenticationError",
    "BrontoBadRequestError",
    "BrontoClient",
    "BrontoConfigError",
    "BrontoConnectionError",
    "BrontoError",
    "BrontoNotFoundError",
    "BrontoPermissionError",
    "BrontoRateLimitError",
    "BrontoServerError",
    "RequestOptions",
    "ingest_base_url",
    "mcp_url",
    "rest_base_url",
    "validate_region",
]
