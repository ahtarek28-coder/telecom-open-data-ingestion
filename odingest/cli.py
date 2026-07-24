"""odingest CLI -- pull real telecom-related public data via legitimate APIs and land it as raw JSON/JSONL."""
from __future__ import annotations

import json
from pathlib import Path

import click

from .checkpoint import load_checkpoint, save_checkpoint
from .fcc_complaints import fetch_complaints, latest_ticket_created
from .http_client import PoliteClient
from .worldbank import DEFAULT_INDICATORS, fetch_indicator


@click.group()
def main() -> None:
    """odingest: pull real telecom-related public data via legitimate, no-auth-required APIs."""


@main.command("fetch-fcc-complaints")
@click.option("--out", "out_dir", default="data/raw/fcc_complaints", show_default=True)
@click.option(
    "--checkpoint", "checkpoint_path", default="data/.checkpoints/fcc_complaints.json", show_default=True
)
@click.option("--page-size", default=1000, show_default=True)
@click.option("--max-pages", default=None, type=int, help="Cap pages fetched (mainly for testing).")
@click.option("--since", default=None, help="ISO timestamp; overrides the checkpoint if given.")
def fetch_fcc_complaints(out_dir, checkpoint_path, page_size, max_pages, since):
    """Fetch FCC consumer complaints, incrementally by default (via checkpoint)."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    since = since or load_checkpoint(checkpoint_path)
    if since:
        click.echo(f"Fetching complaints created after {since} (from checkpoint)")
    else:
        click.echo("No checkpoint found -- fetching from the beginning of the requested window")

    client = PoliteClient()
    total = 0
    newest_seen = since
    out_file = out_path / "complaints.jsonl"
    with out_file.open("a", encoding="utf-8") as f:
        for batch in fetch_complaints(client, since=since, page_size=page_size, max_pages=max_pages):
            for record in batch:
                f.write(json.dumps(record) + "\n")
            total += len(batch)
            batch_newest = latest_ticket_created(batch)
            if batch_newest and (newest_seen is None or batch_newest > newest_seen):
                newest_seen = batch_newest
            click.echo(f"Fetched {len(batch)} record(s) (running total: {total})")

    if newest_seen and newest_seen != since:
        save_checkpoint(checkpoint_path, newest_seen)
        click.echo(f"Checkpoint updated to {newest_seen}")

    click.echo(f"Done: {total} new record(s) appended to {out_file}")


@main.command("fetch-worldbank")
@click.option("--out", "out_dir", default="data/raw/worldbank", show_default=True)
@click.option(
    "--indicator", "indicators", multiple=True, help="Repeatable. Defaults to a built-in telecom indicator set."
)
@click.option("--date-range", default="2015:2024", show_default=True)
def fetch_worldbank(out_dir, indicators, date_range):
    """Fetch World Bank telecom-market indicators (mobile/broadband/internet penetration)."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    indicators = list(indicators) or list(DEFAULT_INDICATORS)

    client = PoliteClient()
    for indicator_id in indicators:
        records = []
        for batch in fetch_indicator(client, indicator_id, date_range=date_range):
            records.extend(batch)
        out_file = out_path / f"{indicator_id}.json"
        out_file.write_text(json.dumps(records))
        click.echo(f"{indicator_id}: {len(records)} record(s) -> {out_file}")


@main.command("load-duckdb")
@click.option("--db", "db_path", default="telecom_open_data.duckdb", show_default=True)
@click.option("--raw-dir", default="data/raw", show_default=True)
def load_duckdb(db_path, raw_dir):
    """Load everything fetched so far into a local DuckDB database."""
    from .load_to_duckdb import load

    load(db_path=db_path, raw_dir=raw_dir)


if __name__ == "__main__":
    main()
