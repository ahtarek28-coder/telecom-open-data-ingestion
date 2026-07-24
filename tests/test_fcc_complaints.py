import responses

from odingest.fcc_complaints import DATASET_URL, fetch_complaints, latest_ticket_created
from odingest.http_client import PoliteClient


def _record(i, created):
    return {"id": str(i), "ticket_created": created, "state": "CA", "issue": "Billing"}


@responses.activate
def test_fetch_complaints_paginates_until_short_page():
    page1 = [_record(i, f"2026-01-0{i}T00:00:00.000Z") for i in range(1, 4)]  # full page
    page2 = [_record(4, "2026-01-04T00:00:00.000Z")]  # short page -> stop

    responses.add(responses.GET, DATASET_URL, json=page1, status=200)
    responses.add(responses.GET, DATASET_URL, json=page2, status=200)

    client = PoliteClient(min_interval_seconds=0)
    batches = list(fetch_complaints(client, page_size=3))

    assert batches == [page1, page2]
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_complaints_stops_on_empty_page():
    responses.add(responses.GET, DATASET_URL, json=[], status=200)

    client = PoliteClient(min_interval_seconds=0)
    batches = list(fetch_complaints(client, page_size=100))

    assert batches == []


@responses.activate
def test_since_param_included_in_request():
    responses.add(responses.GET, DATASET_URL, json=[], status=200)

    client = PoliteClient(min_interval_seconds=0)
    list(fetch_complaints(client, since="2026-01-01T00:00:00.000Z", page_size=100))

    request_url = responses.calls[0].request.url
    assert "ticket_created" in request_url
    assert "2026-01-01" in request_url


@responses.activate
def test_no_since_omits_where_clause():
    responses.add(responses.GET, DATASET_URL, json=[], status=200)

    client = PoliteClient(min_interval_seconds=0)
    list(fetch_complaints(client, page_size=100))

    request_url = responses.calls[0].request.url
    assert "where" not in request_url


def test_latest_ticket_created():
    batch = [
        {"ticket_created": "2026-01-01T00:00:00.000Z"},
        {"ticket_created": "2026-01-03T00:00:00.000Z"},
        {"ticket_created": "2026-01-02T00:00:00.000Z"},
    ]
    assert latest_ticket_created(batch) == "2026-01-03T00:00:00.000Z"


def test_latest_ticket_created_empty():
    assert latest_ticket_created([]) is None
