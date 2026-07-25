# telecom-open-data-ingestion

Ingests real, public, telecom-related data via legitimate no-auth APIs — not scraped HTML — and lands it in DuckDB for analysis:

- **FCC Consumer Complaints** — real telecom complaints (billing, unwanted calls, number portability) filed with the US FCC. Ties back to the `sr_classification` complaint-classification theme in [data-engineering-skills](https://github.com/ahtarek28-coder/data-engineering-skills).
- **World Bank telecom indicators** — mobile/broadband/internet penetration by country and year.

## Status

Fully implemented and verified against the **live** APIs (not mocked, not synthetic): 16/16 unit tests pass (HTTP mocked there, for speed/determinism), and a real run pulled 2,650 rows per World Bank indicator and 3,500 real FCC complaint records across two separate incremental fetches — with zero duplicate records, confirming the checkpoint mechanism actually works.

## Why APIs, not a crawler

This deliberately uses documented, no-auth-required public APIs instead of scraping HTML: no robots.txt ambiguity, no bot-detection to reason about, no ToS risk, and the data is cleaner. Both sources are official open-data programs meant for exactly this kind of programmatic access:
- FCC: [opendata.fcc.gov](https://opendata.fcc.gov/Consumer/CGB-Consumer-Complaints-Data/3xyp-aqkj) (Socrata Open Data API)
- World Bank: [Open Data API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)

## Install

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

Or, if you'd rather not install it as a package: `pip install -r requirements-dev.txt` (or `requirements.txt` for just the runtime deps) — both mirror `pyproject.toml`, kept in sync manually. Either way, `setup_venv.sh` does the `pip install -e ".[dev]"` version of this for you, rebuilding the venv from scratch (safe to rerun any time, including after moving the project folder).

## Usage

```bash
# World Bank telecom indicators (mobile/broadband/internet penetration)
odingest fetch-worldbank

# FCC complaints -- incremental via a checkpoint file; bound the first run
# so you don't pull the entire multi-year history by accident
odingest fetch-fcc-complaints --since 2026-04-01T00:00:00.000Z --max-pages 5 --page-size 500

# Run it again any time after -- it resumes from the checkpoint automatically
odingest fetch-fcc-complaints

# Load everything fetched so far into DuckDB + build analytics views
odingest load-duckdb
```

(If `odingest` isn't on PATH, use `python -m odingest.cli <command>` instead — pip's console-scripts directory isn't always on PATH by default, especially on Windows.)

Then query it:

```bash
python -c "import duckdb; con = duckdb.connect('telecom_open_data.duckdb'); print(con.sql('select * from analytics.complaints_by_state_and_issue limit 10').df())"
python -c "import duckdb; con = duckdb.connect('telecom_open_data.duckdb'); print(con.sql('select * from analytics.mobile_penetration_latest limit 10').df())"
```

## Design notes

- **Politeness by default:** `PoliteClient` enforces a minimum interval between requests, retries transient errors (429/5xx) with exponential backoff, and identifies itself with a real User-Agent — the baseline courtesy expected when hitting a public API repeatedly.
- **Incremental by default:** FCC complaints are fetched via a `$where=ticket_created > :checkpoint` filter, with the checkpoint (the newest `ticket_created` seen) persisted to a JSON file after each run. Re-running only pulls new records — verified live: two runs, 3,500 total records, 0 duplicates.
- **World Bank data isn't incremental the same way** — indicator values get revised over time rather than append-only, so each run does a full refresh per indicator (small dataset, cheap to re-pull).
- **Raw landing format:** FCC complaints append to a single JSONL file (append-only log, matches how the source behaves); World Bank indicators overwrite one JSON file per indicator (matches how that source behaves — small, revisable).

## Tests

```bash
python -m pytest tests/ -v
```

16 tests, all HTTP mocked via `responses` (retry/backoff logic, pagination edge cases, checkpoint round-trips) — no live network calls in the test suite itself, so CI doesn't depend on external APIs staying up or rate-limiting the run.

## Roadmap

- [x] Polite HTTP client (retry/backoff, rate limiting)
- [x] FCC complaints ingestion, incremental via checkpoint
- [x] World Bank indicators ingestion
- [x] DuckDB loader + analytics views
- [x] Unit tests (16/16, mocked HTTP)
- [x] Verified against live APIs, including incremental correctness (0 duplicates across 2 runs)
- [ ] Airflow DAG scheduling regular incremental pulls (natural next step, same pattern as [telecom-cx-analytics-pipeline](https://github.com/ahtarek28-coder/telecom-cx-analytics-pipeline))
- [ ] Join FCC complaint trends with World Bank penetration data for a cross-source view
