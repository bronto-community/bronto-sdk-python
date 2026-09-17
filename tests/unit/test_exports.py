"""Tests that the public API surface is exported and stays side-effect free."""

import bronto_sdk


def test_clients_are_exported():
    assert bronto_sdk.BrontoClient is not None
    assert bronto_sdk.AsyncBrontoClient is not None


def test_request_options_is_exported():
    assert "RequestOptions" in bronto_sdk.__all__
    assert bronto_sdk.RequestOptions is not None


def test_all_names_are_importable():
    for name in bronto_sdk.__all__:
        assert hasattr(bronto_sdk, name), name


def test_mcp_subpackage_is_importable_but_not_imported_eagerly():
    # `import bronto_sdk` must stay side-effect free: the subpackage is reached
    # explicitly, like `domain` and `models`.
    from bronto_sdk import mcp

    assert mcp.__all__ == ["auth_headers", "url"]
    for name in mcp.__all__:
        assert hasattr(mcp, name), name
