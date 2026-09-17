"""Tests that the models subpackage's public surface is complete and lenient.

The `extra="allow"` assertion is the important one: it is the SDK's single
forward-compatibility guarantee, and a model added later that forgets it would
otherwise break consumers silently the next time the API grows a field.
"""

import pydantic
import pytest

import bronto_sdk.models as models
from bronto_sdk.models import SearchRequest
from bronto_sdk.models._common import ReadModel


def test_every_exported_name_is_importable():
    for name in models.__all__:
        assert hasattr(models, name), name


def test_all_is_sorted():
    assert models.__all__ == sorted(models.__all__)


def test_every_exported_name_is_a_model():
    for name in models.__all__:
        assert issubclass(getattr(models, name), pydantic.BaseModel), name


@pytest.mark.parametrize("name", sorted(models.__all__))
def test_every_model_allows_unknown_fields(name):
    model = getattr(models, name)
    assert model.model_config.get("extra") == "allow", (
        f"{name} would reject a field the API adds later"
    )


def test_the_shared_base_is_not_exported():
    assert "ReadModel" not in models.__all__


def test_read_models_do_not_match_aliases_by_python_field_name():
    # Keyed off the base class rather than a list of write-model names, so a
    # second write model does not silently fall through the check.
    for name in models.__all__:
        model = getattr(models, name)
        if issubclass(model, ReadModel):
            assert not model.model_config.get("populate_by_name"), name


def test_the_request_model_does_match_by_python_field_name():
    assert SearchRequest.model_config.get("populate_by_name") is True
