"""Tests for the /search response models."""

from bronto_sdk.models import GroupSeriesItem, SearchResponse

FULL_RESPONSE = {
    "explain": {
        "Execution time (millis)": "353",
        "Bytes searched": "356215",
        "Matching events": "4",
    },
    "events": [
        {
            "@raw": '10.0.108.203 - - "GET / HTTP/1.1" 200 675',
            "@time": "2024-05-27 23:26:34.331 UTC",
            "@status": "info",
            "message_kvs": {"method": "GET", "status_code": "200"},
            "attributes": {"$environment": "production", "team": "mickey 17"},
            "metadata": {
                "service_id": "23746675-7022-4985-bd74-4af9eba58d72",
                "timestamp": 1716853347801,
                "sequence": 9135279166383456256,
            },
        }
    ],
    "groups_series": [
        {
            "key": "hostname",
            "name": "host123",
            "count": 124,
            "stat": "average(duration_millis)",
            "value": 50325.25,
            "quantiles": {"min": 691.0, "p50": 796.0, "max": 1331.0},
            "timeseries": [
                {"@timestamp": 1711535140632, "count": 40, "value": 35.625},
                {"@timestamp": 1711535200632, "count": 12, "value": 18.5},
            ],
            "groups_series": [
                {"name": "eu-west-1", "count": 60, "value": 25000.0},
            ],
            "delta": {"total_count": 0, "delta_factor": 0.0},
        }
    ],
    "metadata": {
        "select": ["host", "status", "method"],
        "correlation_id": "00000000-0000-0000-0000-000000000000",
    },
    "totals": {
        "count": 98,
        "max(latency_ms)": 1830.0,
        "total_groups": 7.0,
        "retrieved_groups": 4.0,
        "timeseries": [{"@timestamp": 1711535140632, "count": 98, "quantiles": {}}],
    },
    "pagination": {"next_page_url": "https://api.eu.bronto.io/search?token=abc"},
    "links": [{"rel": "next", "href": "https://api.eu.bronto.io/search?token=abc"}],
    "answer": [],
    "is_exact": True,
}


def test_the_full_envelope_round_trips_without_loss():
    # Dict equality, not json.dumps string equality: pydantic emits fields in
    # declaration order with extras last, so key order legitimately differs
    # from the input while every key and value is preserved.
    response = SearchResponse.model_validate(FULL_RESPONSE)
    assert response.model_dump(by_alias=True, exclude_none=True) == FULL_RESPONSE


def test_at_prefixed_keys_populate_fields_rather_than_extras():
    events = SearchResponse.model_validate(FULL_RESPONSE).events
    assert events is not None
    event = events[0]
    assert event.time == "2024-05-27 23:26:34.331 UTC"
    assert event.raw == '10.0.108.203 - - "GET / HTTP/1.1" 200 675'
    assert "@raw" not in (event.model_extra or {})


def test_the_bare_timestamp_spelling_is_not_captured_or_renamed():
    payload = {"groups_series": [{"timeseries": [{"timestamp": 1711535140632}]}]}
    response = SearchResponse.model_validate(payload)
    assert response.groups_series is not None
    timeseries = response.groups_series[0].timeseries
    assert timeseries is not None
    assert timeseries[0].timestamp is None
    assert timeseries[0].model_extra == {"timestamp": 1711535140632}
    assert response.model_dump(by_alias=True, exclude_none=True) == payload


def test_the_select_projection_is_readable_from_an_event():
    # A `select` projects into the event itself, split by origin: fields
    # parsed from the log message land in `message_kvs`, details attached at
    # ingestion in `attributes`. There is no separate array to consult. Note
    # `team` — an attribute key needs no "$" prefix; that marks Bronto's own.
    response = SearchResponse.model_validate(FULL_RESPONSE)
    assert response.events is not None
    event = response.events[0]
    assert event.message_kvs == {"method": "GET", "status_code": "200"}
    assert event.attributes == {"$environment": "production", "team": "mickey 17"}


def test_group_series_nest_recursively():
    response = SearchResponse.model_validate(FULL_RESPONSE)
    assert response.groups_series is not None
    children = response.groups_series[0].groups_series
    assert children is not None
    nested = children[0]
    assert isinstance(nested, GroupSeriesItem)
    assert nested.name == "eu-west-1"
    assert nested.count == 60


def test_unknown_fields_survive_at_every_depth():
    payload = {
        "brand_new_top_level": 1,
        "events": [{"@raw": "x", "brand_new_row_field": 2}],
        "totals": {"count": 3, "brand_new_total": 4},
    }
    response = SearchResponse.model_validate(payload)
    assert response.events is not None
    assert response.totals is not None
    assert response.model_extra == {"brand_new_top_level": 1}
    assert response.events[0].model_extra == {"brand_new_row_field": 2}
    assert response.totals.model_extra == {"brand_new_total": 4}


def test_truncation_signal_is_readable():
    # total_groups vs retrieved_groups is the only indication that a `limit`
    # cut the group list short, and both arrive as floats.
    totals = SearchResponse.model_validate(FULL_RESPONSE).totals
    assert totals is not None
    assert totals.total_groups == 7.0
    assert totals.retrieved_groups == 4.0
    assert totals.model_extra is not None
    assert totals.model_extra["max(latency_ms)"] == 1830.0


def test_a_time_slice_carrying_value_count_and_quantiles_is_accepted():
    response = SearchResponse.model_validate(
        {
            "groups_series": [
                {
                    "timeseries": [
                        {
                            "@timestamp": 1711535140632,
                            "count": 40,
                            "value": 35.625,
                            "quantiles": {},
                        }
                    ]
                }
            ]
        }
    )
    assert response.groups_series is not None
    timeseries = response.groups_series[0].timeseries
    assert timeseries is not None
    slice_ = timeseries[0]
    assert slice_.count == 40
    assert slice_.value == 35.625
    assert slice_.quantiles == {}


def test_explain_exposes_the_declared_and_the_live_only_keys():
    explain = SearchResponse.model_validate(FULL_RESPONSE).explain
    assert explain is not None
    assert explain.execution_time_millis == "353"
    assert explain.bytes_searched == "356215"
    assert explain.matching_events == "4"


def test_explain_only_diagnostics_survive_as_extras():
    explain = SearchResponse.model_validate(
        {"explain": {"Approximate bytes in time range": "9000"}}
    ).explain
    assert explain is not None
    assert explain.model_extra == {"Approximate bytes in time range": "9000"}


def test_an_empty_response_parses_to_all_none():
    response = SearchResponse.model_validate({})
    assert response.events is None
    assert response.groups_series is None
    assert response.model_dump(by_alias=True, exclude_none=True) == {}


def test_the_legacy_arrays_still_parse_untyped():
    # `result` and `groups` are dropped from the SDK's contract, not rejected:
    # the API still populates them for older clients, and a response carrying
    # them must keep parsing. They land in `model_extra`, unsupported.
    payload = {
        "events": [{"@raw": "x"}],
        "result": [{"@time": "2024-03-27 10:25:40.632 UTC"}],
        "groups": [{"group": "[US]", "count": 124}],
        "answer": [],
    }
    response = SearchResponse.model_validate(payload)
    assert response.events is not None
    assert response.model_extra is not None
    assert set(response.model_extra) == {"result", "groups", "answer"}
    assert response.model_dump(by_alias=True, exclude_none=True) == payload
