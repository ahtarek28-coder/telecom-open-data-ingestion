"""
Ingestion for the World Bank's public Open Data API -- telecom-market
context indicators (mobile/broadband/internet penetration) across countries
and years. No API key required.

Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""
from __future__ import annotations

from typing import Iterator

BASE_URL = "https://api.worldbank.org/v2/country/all/indicator/{indicator}"

# A handful of well-known, stable telecom-relevant indicator codes.
DEFAULT_INDICATORS = {
    "IT.CEL.SETS.P2": "Mobile cellular subscriptions (per 100 people)",
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "IT.NET.BBND.P2": "Fixed broadband subscriptions (per 100 people)",
}


def fetch_indicator(
    client,
    indicator_id: str,
    date_range: str | None = None,
    per_page: int = 1000,
    max_pages: int | None = None,
) -> Iterator[list[dict]]:
    """
    Yields pages (lists of dicts) of {country, date, value} records for the
    given indicator. `date_range` is a World Bank-style range, e.g. "2015:2024".
    """
    url = BASE_URL.format(indicator=indicator_id)
    page = 1
    while max_pages is None or page <= max_pages:
        params = {"format": "json", "per_page": per_page, "page": page}
        if date_range:
            params["date"] = date_range

        response = client.get(url, params=params)
        payload = response.json()

        # The API returns [metadata, data] on success, or a single dict with
        # a "message" key on error (e.g. an unknown indicator code).
        if isinstance(payload, dict) and "message" in payload:
            raise ValueError(f"World Bank API error for indicator '{indicator_id}': {payload['message']}")

        metadata, data = payload
        if not data:
            return

        yield data

        if page >= metadata.get("pages", page):
            return
        page += 1
