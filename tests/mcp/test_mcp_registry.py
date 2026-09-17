"""Tests for the MCP endpoint registry.

The golden URLs here are the exact strings four sibling projects hardcode
today; they are asserted verbatim so a migration to this registry is provably
a no-op on the wire.
"""

import pytest

from bronto_sdk import BrontoConfigError, mcp


def test_region_urls_match_the_strings_consumers_hardcode_today():
    assert mcp.url("eu") == "https://mcp.eu.bronto.io/mcp"
    assert mcp.url("us") == "https://mcp.us.bronto.io/mcp"


def test_a_new_region_works_without_an_sdk_release():
    # Unlike the consumers' closed dict, an unknown-but-valid slug resolves.
    assert mcp.url("us-2") == "https://mcp.us-2.bronto.io/mcp"


@pytest.mark.parametrize(
    "base_url",
    ["https://mcp.eu.staging.bronto.io", "https://mcp.eu.staging.bronto.io/"],
)
def test_base_url_reaches_the_staging_tier_the_region_slug_cannot(base_url):
    # 'eu.staging' is rejected by validate_region (the dot is exactly the
    # host-smuggling character), so base_url is the only way to name this host.
    assert mcp.url(base_url=base_url) == "https://mcp.eu.staging.bronto.io/mcp"


def test_base_url_wins_over_region():
    # Same precedence as BrontoClient, so both answer this input identically.
    assert (
        mcp.url("eu", base_url="https://mcp.us.staging.bronto.io")
        == "https://mcp.us.staging.bronto.io/mcp"
    )


def test_no_endpoint_configured_raises():
    with pytest.raises(BrontoConfigError) as excinfo:
        mcp.url()
    assert "base_url" in str(excinfo.value)


@pytest.mark.parametrize("malicious", ["evil.com/", "evil.com", "us@evil.com", "US"])
def test_region_host_smuggling_is_rejected(malicious):
    with pytest.raises(BrontoConfigError):
        mcp.url(malicious)


def test_api_key_header():
    assert mcp.auth_headers(api_key="k") == {"X-BRONTO-API-KEY": "k"}


def test_bearer_header_is_sent_verbatim():
    assert mcp.auth_headers(bearer_token="Bearer jwt") == {
        "Authorization": "Bearer jwt"
    }


def test_bearer_wins_over_api_key():
    assert mcp.auth_headers(api_key="k", bearer_token="jwt") == {"Authorization": "jwt"}


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"api_key": ""}, {"bearer_token": ""}, {"api_key": "", "bearer_token": ""}],
)
def test_missing_or_empty_credential_fails_closed(kwargs):
    with pytest.raises(BrontoConfigError):
        mcp.auth_headers(**kwargs)


def test_exactly_one_header_is_emitted():
    # Never two credentials on one request, whatever the caller passes.
    assert len(mcp.auth_headers(api_key="k", bearer_token="jwt")) == 1
