"""Simple JSON-file checkpoint storage for incremental ingestion."""
from __future__ import annotations

import json
from pathlib import Path


def load_checkpoint(path: str | Path) -> str | None:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text()).get("last_value")


def save_checkpoint(path: str | Path, value: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_value": value}))
