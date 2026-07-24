"""
Ingestion for the FCC's public Consumer Complaints Data -- real telecom
complaints (phone/cable/wireless: billing, unwanted calls, number
portability, etc.) via the Socrata Open Data (SODA) API.

Dataset: https://opendata.fcc.gov/Consumer/CGB-Consumer-Complaints-Data/3xyp-aqkj
No API key required for the request volumes this project makes; set
FCC_APP_TOKEN for a Socrata app token if you want higher rate limits.
"""
from __future__ import annotations

import os
from typing import Iterator

from .http_client import PoliteClient

DATASET_URL = "https://opendata.fcc.gov/resource/3xyp-aqkj.json"


def fetch_complaints(
    client: PoliteClient,
    since: str | None = None,
    page_size: int = 1000,
    max_pages: int | None = None,
    app_token: str | None = None,
) -> Iterator[list[dict]]:
    """
    Yields batches (lists of dicts) of complaint records, ordered by
    ticket_created ascending. If `since` (an ISO 8601 timestamp) is given,
    only records created after it are fetched -- this is what makes repeated
    runs incremental instead of re-pulling the whole dataset every time.
    """
    app_token = app_token or os.environ.get("FCC_APP_TOKEN")
    headers = {"X-App-Token": app_token} if app_token else None

    offset = 0
    page = 0
    while max_pages is None or page < max_pages:
        params = {
            "$limit": page_size,
            "$offset": offset,
            "$order": "ticket_created ASC",
        }
        if since:
            params["$where"] = f"ticket_created > '{since}'"

        response = client.get(DATASET_URL, params=params, headers=headers)
        batch = response.json()
        if not batch:
            return

        yield batch
        page += 1
        offset += page_size

        if len(batch) < page_size:
            return  # last page


def latest_ticket_created(batch: list[dict]) -> str | None:
    """Returns the max ticket_created timestamp in a batch, for checkpointing."""
    timestamps = [r["ticket_created"] for r in batch if r.get("ticket_created")]
    return max(timestamps) if timestamps else None
