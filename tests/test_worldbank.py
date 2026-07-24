import pytest
import responses

from odingest.http_client import PoliteClient
from odingest.worldbank import BASE_URL, fetch_indicator

INDICATOR = "IT.CEL.SETS.P2"
URL = BASE_URL.format(indicator=INDICATOR)


def _metadata(page, pages):
    return {
        "page": page,
        "pages": pages,
        "per_page": 2,
        "total": pages * 2,
        "sourceid": "2",
        "lastupdated": "2026-01-01",
    }


def _record(country, value):
    return {
        "indicator": {"id": INDICATOR, "value": "Mobile cellular subscriptions (per 100 people)"},
        "country": {"id": country, "value": country},
        "date": "2024",
        "value": value,
    }


@responses.activate
def test_fetch_indicator_paginates_across_pages():
    page1 = [_metadata(1, 2), [_record("US", 100.0), _record("CA", 90.0)]]
    page2 = [_metadata(2, 2), [_record("MX", 80.0)]]
    responses.add(responses.GET, URL, json=page1, status=200)
    responses.add(responses.GET, URL, json=page2, status=200)

    client = PoliteClient(min_interval_seconds=0)
    batches = list(fetch_indicator(client, INDICATOR))

    assert batches == [page1[1], page2[1]]
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_indicator_stops_when_data_empty():
    page1 = [_metadata(1, 1), []]
    responses.add(responses.GET, URL, json=page1, status=200)

    client = PoliteClient(min_interval_seconds=0)
    batches = list(fetch_indicator(client, INDICATOR))

    assert batches == []


@responses.activate
def test_fetch_indicator_raises_on_api_error_message():
    responses.add(responses.GET, URL, json={"message": "Invalid indicator"}, status=200)

    client = PoliteClient(min_interval_seconds=0)
    with pytest.raises(ValueError, match="Invalid indicator"):
        list(fetch_indicator(client, INDICATOR))


@responses.activate
def test_fetch_indicator_stops_after_last_page():
    page1 = [_metadata(1, 1), [_record("US", 100.0)]]
    responses.add(responses.GET, URL, json=page1, status=200)

    client = PoliteClient(min_interval_seconds=0)
    batches = list(fetch_indicator(client, INDICATOR))

    assert batches == [page1[1]]
    assert len(responses.calls) == 1
