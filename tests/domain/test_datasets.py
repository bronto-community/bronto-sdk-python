"""Tests for dataset domain helpers.

The REST and MCP APIs name a dataset's fields differently; project_dataset
must reduce either shape to the same triple.
"""

from bronto_sdk.domain import project_dataset


def test_project_dataset_reads_the_mcp_shape():
    mcp = {"log_id": "l-1", "name": "orders", "collection": "app-logs", "extra": 1}
    assert project_dataset(mcp) == {
        "log_id": "l-1",
        "name": "orders",
        "collection": "app-logs",
    }


def test_project_dataset_reads_the_rest_shape():
    rest = {"id": "l-1", "dataset": "orders", "collection": "app-logs"}
    assert project_dataset(rest) == {
        "log_id": "l-1",
        "name": "orders",
        "collection": "app-logs",
    }


def test_project_dataset_prefers_mcp_field_names_when_both_present():
    # A hypothetical object carrying both spellings resolves to the MCP names,
    # matching the fallback order documented on the function.
    both = {
        "log_id": "mcp-id",
        "id": "rest-id",
        "name": "mcp-name",
        "dataset": "rest-name",
        "collection": "app-logs",
    }
    assert project_dataset(both) == {
        "log_id": "mcp-id",
        "name": "mcp-name",
        "collection": "app-logs",
    }


def test_project_dataset_missing_fields_become_none():
    assert project_dataset({}) == {"log_id": None, "name": None, "collection": None}
