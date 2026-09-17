"""Single source of truth for the package version at runtime.

Kept in a module of its own so importing the version never pulls in httpx or
pydantic. `just update-version` rewrites this file, `VERSION`, and the
`version` field in `pyproject.toml` together.
"""

VERSION = "0.1.1"
