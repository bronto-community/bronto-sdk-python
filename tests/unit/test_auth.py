"""Tests for credential-header rendering and identity headers."""

import bronto_sdk
from bronto_sdk._auth import credential_header, user_agent


def test_bearer_scheme_renders_authorization():
    assert credential_header("bearer", "jwt") == {"Authorization": "jwt"}


def test_api_key_scheme_renders_bronto_header():
    assert credential_header("api_key", "k") == {"X-BRONTO-API-KEY": "k"}


def test_user_agent_is_tied_to_version():
    assert user_agent() == f"bronto-sdk-python/{bronto_sdk.VERSION}"
