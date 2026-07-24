import pytest
import requests
import responses

from odingest.http_client import PoliteClient, RetryConfig

URL = "https://example.com/data"


@responses.activate
def test_get_succeeds_first_try():
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    client = PoliteClient(min_interval_seconds=0)

    resp = client.get(URL)

    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 1


@responses.activate
def test_retries_on_500_then_succeeds():
    responses.add(responses.GET, URL, status=500)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    client = PoliteClient(
        min_interval_seconds=0, retry_config=RetryConfig(max_attempts=3, backoff_base_seconds=0)
    )

    resp = client.get(URL)

    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_raises_after_exhausting_retries():
    for _ in range(3):
        responses.add(responses.GET, URL, status=503)
    client = PoliteClient(
        min_interval_seconds=0, retry_config=RetryConfig(max_attempts=3, backoff_base_seconds=0)
    )

    with pytest.raises(requests.exceptions.HTTPError):
        client.get(URL)
    assert len(responses.calls) == 3


@responses.activate
def test_non_retryable_error_raises_immediately():
    responses.add(responses.GET, URL, status=404)
    client = PoliteClient(min_interval_seconds=0)

    with pytest.raises(requests.exceptions.HTTPError):
        client.get(URL)
    assert len(responses.calls) == 1
