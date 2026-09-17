"""Guards against a large integer ever being typed `float`.

Bronto sequence numbers exceed 2**53, where a float silently rounds.

Two kinds of test here. The payload tests prove a real 19-digit value survives.
The introspection test walks every model's annotations, so a field added later
with the wrong type fails without anyone having to write a payload for it.
"""

import json
import typing

import pytest

import bronto_sdk.models as models
from bronto_sdk.models import (
    Event,
    HistogramBucket,
    MonitorEvent,
    SearchResponse,
    TimeSlice,
)

BIG_SEQUENCE = 9135279166383456256

BIG_INTEGER_FIELDS = frozenset(
    {
        "created_at",
        "deleted_at",
        "from_sequence",
        "from_ts",
        "group_retention",
        "last_heartbeat_at",
        "last_trigger_ts",
        "modified_at",
        "muted_until",
        "sequence",
        "time",
        "timestamp",
        "to_ts",
    }
)


def _annotation_types(annotation):
    """Flatten a possibly-optional, possibly-union annotation to a type set."""
    args = typing.get_args(annotation)
    return set(args) if args else {annotation}


@pytest.mark.parametrize("name", sorted(models.__all__))
def test_no_large_integer_field_is_annotated_float(name):
    model = getattr(models, name)
    for field_name, field in model.model_fields.items():
        if field_name in BIG_INTEGER_FIELDS:
            assert float not in _annotation_types(field.annotation), (
                f"{name}.{field_name} admits float; a value above 2**53 would round"
            )


@pytest.mark.parametrize(
    ("model", "field_name"),
    [(HistogramBucket, "value"), (TimeSlice, "count")],
)
def test_count_fields_declared_number_in_the_spec_are_ints(model, field_name):
    # The spec types HistogramBucket.value as `number, format: int64`. It is an
    # event count, so the SDK narrows it to int rather than following the spec.
    annotation = model.model_fields[field_name].annotation
    assert float not in _annotation_types(annotation)
    assert int in _annotation_types(annotation)


def test_an_integer_sequence_stays_an_integer_and_keeps_every_digit():
    event = Event.model_validate({"metadata": {"sequence": BIG_SEQUENCE}})
    assert event.metadata is not None
    assert isinstance(event.metadata.sequence, int)
    assert json.dumps(event.model_dump(by_alias=True, exclude_none=True)) == (
        f'{{"metadata": {{"sequence": {BIG_SEQUENCE}}}}}'
    )


def test_a_time_slice_timestamp_is_an_int_whichever_wire_type_arrives():
    # The spec declares @timestamp a string; the API sends a number. Narrowing
    # to int is safe because Python ints are arbitrary-precision, so a numeric
    # string converts without losing a digit — which a float would not.
    assert TimeSlice.model_validate({"@timestamp": 1711535140632}).timestamp == (
        1711535140632
    )
    from_string = TimeSlice.model_validate({"@timestamp": str(BIG_SEQUENCE)})
    assert from_string.timestamp == BIG_SEQUENCE
    assert isinstance(from_string.timestamp, int)


def test_a_monitor_event_time_survives_as_an_integer():
    event = MonitorEvent.model_validate({"time": 1724336885000})
    assert event.time == 1724336885000
    assert isinstance(event.time, int)


def test_the_whole_response_preserves_a_big_sequence_end_to_end():
    payload = {
        "events": [{"metadata": {"sequence": BIG_SEQUENCE}}],
    }
    dumped = SearchResponse.model_validate(payload).model_dump(
        by_alias=True, exclude_none=True
    )
    assert json.dumps(dumped) == json.dumps(payload)


def test_float_is_why_this_file_exists():
    # The counterexample the guards above protect against. Both values are real
    # shapes: a 19-digit sequence, and the epoch-ms figure bronto-cli watched
    # change under a float64 round trip.
    assert int(float(9135279166383456257)) == 9135279166383456256
    assert int(float(1711535140632516544)) == 1711535140632516608
    # A float also stops being an integer on the wire, even when exact.
    assert json.dumps(float(BIG_SEQUENCE)) == "9.135279166383456e+18"
