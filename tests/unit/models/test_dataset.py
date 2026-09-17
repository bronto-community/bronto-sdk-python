"""Tests for the dataset models."""

from bronto_sdk.domain import project_dataset
from bronto_sdk.models import Dataset, DatasetsResponse

# A live REST dataset. Note `parser_id` is the empty string, not a UUID.
LIVE_DATASET = {
    "id": "ac046803-ca24-93fe-5598-15ee147e94f9",
    "collection": "foo",
    "dataset": "bar",
    "is_system_generated": False,
    "tags": {"service": "gateway", "team": "mickey 17"},
    "parser_id": "",
    "metadata": {"last_heartbeat_at": 1785153016033},
}


def test_a_live_dataset_round_trips_without_loss():
    assert (
        Dataset.model_validate(LIVE_DATASET).model_dump(
            by_alias=True, exclude_none=True
        )
        == LIVE_DATASET
    )


def test_an_unparsed_dataset_keeps_its_empty_parser_id():
    assert Dataset.model_validate(LIVE_DATASET).parser_id == ""


def test_the_heartbeat_is_readable_through_the_audit_block():
    dataset = Dataset.model_validate(LIVE_DATASET)
    assert dataset.metadata is not None
    assert dataset.metadata.last_heartbeat_at == 1785153016033


def test_datasets_response_handles_absent_and_empty_lists():
    assert DatasetsResponse.model_validate({}).datasets is None
    assert DatasetsResponse.model_validate({"datasets": []}).datasets == []


def test_an_unknown_dataset_field_survives():
    dataset = Dataset.model_validate({**LIVE_DATASET, "retention_days": 30})
    assert dataset.model_extra == {"retention_days": 30}


def test_the_domain_projection_still_works_on_a_dumped_model():
    dataset = Dataset.model_validate(LIVE_DATASET)
    assert project_dataset(dataset.model_dump(by_alias=True)) == {
        "log_id": LIVE_DATASET["id"],
        "name": LIVE_DATASET["dataset"],
        "collection": LIVE_DATASET["collection"],
    }
