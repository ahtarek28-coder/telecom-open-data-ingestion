"""
A small, polite HTTP client wrapper: identifies itself with a real User-Agent,
retries on transient errors (429/5xx) with exponential backoff, and enforces
a minimum delay between requests -- the baseline courtesy expected when
pulling from public APIs repeatedly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import requests

DEFAULT_USER_AGENT = (
    "telecom-open-data-ingestion/0.1 "
    "(https://github.com/ahtarek28-coder/telecom-open-data-ingestion; portfolio project)"
)


@dataclass
class RetryConfig:
    max_attempts: int = 5
    backoff_base_seconds: float = 1.0
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


class PoliteClient:
    """Wraps requests.Session with retry/backoff and a minimum request interval."""

    def __init__(
        self,
        min_interval_seconds: float = 0.5,
        retry_config: RetryConfig | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        session: requests.Session | None = None,
    ) -> None:
        self.min_interval_seconds = min_interval_seconds
        self.retry_config = retry_config or RetryConfig()
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_time: float | None = None

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_time is None:
            return
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float = 30.0,
    ) -> requests.Response:
        """GET with retry/backoff on transient errors and a minimum request interval."""
        last_exc: Exception | None = None
        for attempt in range(1, self.retry_config.max_attempts + 1):
            self._wait_for_rate_limit()
            self._last_request_time = time.monotonic()
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=timeout)
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt == self.retry_config.max_attempts:
                    raise
                time.sleep(self.retry_config.backoff_base_seconds * (2 ** (attempt - 1)))
                continue

            if response.status_code not in self.retry_config.retry_on_status:
                response.raise_for_status()
                return response

            if attempt == self.retry_config.max_attempts:
                response.raise_for_status()
            time.sleep(self.retry_config.backoff_base_seconds * (2 ** (attempt - 1)))

        # Unreachable in practice -- max_attempts >= 1 always returns or raises above.
        raise last_exc or RuntimeError("Request failed with no response and no exception")
