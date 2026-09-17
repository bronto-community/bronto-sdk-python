"""Tests for region validation and regional URL construction.

The host-smuggling guard is the reason this module exists, so it is tested
first: a region slug is interpolated straight into a hostname, and a value
containing a slash, ``@``, dot, colon, or whitespace would move the host off
``bronto.io`` and leak the credential to an attacker.
"""

import pytest

from bronto_sdk import (
    BrontoConfigError,
    ingest_base_url,
    mcp_url,
    rest_base_url,
    validate_region,
)


@pytest.mark.parametrize(
    "malicious",
    [
        "evil.com/",
        "evil.com",  # a dot alone escapes the api.<region>.bronto.io shape
        "us/../evil",
        "us@evil.com",
        "us:8080",
        "us ",
        " us",
        "us\tx",
        "US",  # uppercase is excluded by the slug pattern
        "-us",  # must start alphanumeric
        "",
    ],
)
def test_host_smuggling_is_rejected(malicious):
    with pytest.raises(BrontoConfigError):
        validate_region(malicious)


def test_evil_region_never_yields_attacker_host():
    with pytest.raises(BrontoConfigError):
        rest_base_url("evil.com/")


def test_config_error_names_the_bad_value_and_points_at_base_url():
    with pytest.raises(BrontoConfigError) as excinfo:
        validate_region("Evil/")
    message = str(excinfo.value)
    assert "'Evil/'" in message
    assert "base_url" in message


@pytest.mark.parametrize("region", ["eu", "us", "us-2", "us2", "a"])
def test_valid_slugs_are_accepted(region):
    assert validate_region(region) == region


def test_rest_base_url():
    assert rest_base_url("eu") == "https://api.eu.bronto.io"
    assert rest_base_url("us-2") == "https://api.us-2.bronto.io"


def test_mcp_url():
    assert mcp_url("us") == "https://mcp.us.bronto.io/mcp"


def test_ingest_base_url_is_a_distinct_host():
    assert ingest_base_url("eu") == "https://ingestion.eu.bronto.io"


@pytest.mark.parametrize("builder", [rest_base_url, mcp_url, ingest_base_url])
def test_url_builders_validate_first(builder):
    with pytest.raises(BrontoConfigError):
        builder("evil.com/")
