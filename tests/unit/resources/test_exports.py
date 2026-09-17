"""Guards on the resource surface and on sync/async accessor parity."""

import inspect

import bronto_sdk
from bronto_sdk import resources

ACCESSORS = ("search", "monitors", "datasets")


def test_all_names_are_importable():
    for name in resources.__all__:
        assert hasattr(resources, name), name


def test_all_is_sorted():
    assert resources.__all__ == sorted(resources.__all__)


def test_resources_are_not_re_exported_from_the_root():
    # The accessor is the entry point; the classes exist to be named in an
    # annotation, not to widen the root surface.
    for name in resources.__all__:
        assert name not in bronto_sdk.__all__


def test_both_clients_expose_the_same_accessors():
    for name in ACCESSORS:
        assert isinstance(
            inspect.getattr_static(bronto_sdk.BrontoClient, name),
            type(inspect.getattr_static(bronto_sdk.AsyncBrontoClient, name)),
        )
        assert hasattr(bronto_sdk.BrontoClient, name)
        assert hasattr(bronto_sdk.AsyncBrontoClient, name)


def test_accessor_methods_mirror_each_other():
    # Sync and async are mirrors: identical method names and identical
    # signatures, so a fifth operation cannot land on one client only.
    client = bronto_sdk.BrontoClient(api_key="k", region="eu")
    async_client = bronto_sdk.AsyncBrontoClient(api_key="k", region="eu")
    for name in ACCESSORS:
        sync_resource = getattr(client, name)
        async_resource = getattr(async_client, name)
        sync_methods = {m for m in dir(sync_resource) if not m.startswith("_")}
        assert sync_methods == {m for m in dir(async_resource) if not m.startswith("_")}
        for method in sync_methods:
            assert inspect.signature(getattr(sync_resource, method)) == (
                inspect.signature(getattr(async_resource, method))
            )
            assert inspect.iscoroutinefunction(getattr(async_resource, method))
    client.close()


def test_accessors_are_cached():
    client = bronto_sdk.BrontoClient(api_key="k", region="eu")
    assert client.search is client.search
    assert client.monitors is client.monitors
    assert client.datasets is client.datasets
    client.close()
