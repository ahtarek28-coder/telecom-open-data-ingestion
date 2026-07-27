"""Loads raw ingested JSON/JSONL data into a local DuckDB database, plus a
couple of convenience analytics views on top."""
from __future__ import annotations

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "telecom_open_data.duckdb"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load(db_path: str | Path = DEFAULT_DB_PATH, raw_dir: str | Path = DEFAULT_RAW_DIR) -> None:
    db_path = Path(db_path)
    raw_dir = Path(raw_dir)
    con = duckdb.connect(str(db_path))
    con.execute("create schema if not exists raw")
    con.execute("create schema if not exists analytics")

    _load_fcc_complaints(con, raw_dir)
    _load_worldbank(con, raw_dir)

    con.close()


def _load_fcc_complaints(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    complaints_file = raw_dir / "fcc_complaints" / "complaints.jsonl"
    if not complaints_file.exists() or complaints_file.stat().st_size == 0:
        print(f"Skipped fcc_complaints: no data at {complaints_file}")
        return

    # complaints.jsonl is an append-only log written across possibly many
    # ingestion runs -- retries, overlapping manual triggers, or a checkpoint
    # race can all cause the same complaint to get appended more than once.
    # Deduplicate by id at load time so raw.fcc_complaints always represents
    # distinct complaints regardless of how messy the raw log gets.
    con.execute(
        f"""
        create or replace table raw.fcc_complaints as
        select * exclude (_dq_row_num) from (
            select *, row_number() over (partition by id order by ticket_created desc) as _dq_row_num
            from read_json_auto('{complaints_file.as_posix()}', format='newline_delimited')
        )
        where _dq_row_num = 1
        """
    )
    n = con.execute("select count(*) from raw.fcc_complaints").fetchone()[0]
    print(f"Loaded raw.fcc_complaints: {n:,} rows (deduplicated by id)")

    con.execute(
        """
        create or replace view analytics.complaints_by_state_and_issue as
        select state, issue_type, method, issue, count(*) as complaint_count
        from raw.fcc_complaints
        where state is not null
        group by 1, 2, 3, 4
        order by complaint_count desc
        """
    )
    print("Created analytics.complaints_by_state_and_issue")


def _load_worldbank(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    worldbank_dir = raw_dir / "worldbank"
    indicator_files = sorted(worldbank_dir.glob("*.json")) if worldbank_dir.exists() else []
    if not indicator_files:
        print(f"Skipped worldbank: no files in {worldbank_dir}")
        return

    con.execute(
        """
        create or replace table raw.worldbank_indicators (
            indicator_id varchar,
            indicator_name varchar,
            country_id varchar,
            country_name varchar,
            date varchar,
            value double
        )
        """
    )
    for f in indicator_files:
        indicator_id = f.stem
        con.execute(
            f"""
            insert into raw.worldbank_indicators
            select
                '{indicator_id}' as indicator_id,
                indicator.value as indicator_name,
                country.id as country_id,
                country.value as country_name,
                date,
                value
            from read_json_auto('{f.as_posix()}')
            """
        )
    n = con.execute("select count(*) from raw.worldbank_indicators").fetchone()[0]
    print(f"Loaded raw.worldbank_indicators: {n:,} rows")

    con.execute(
        """
        create or replace view analytics.mobile_penetration_latest as
        with ranked as (
            select
                country_name,
                country_id,
                value as mobile_subs_per_100,
                date,
                row_number() over (partition by country_id order by date desc) as rn
            from raw.worldbank_indicators
            where indicator_id = 'IT.CEL.SETS.P2' and value is not null
        )
        select country_name, date as latest_year, mobile_subs_per_100
        from ranked
        where rn = 1
        order by mobile_subs_per_100 desc
        """
    )
    print("Created analytics.mobile_penetration_latest")


if __name__ == "__main__":
    load()
