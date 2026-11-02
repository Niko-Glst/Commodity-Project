"""The forecast log: every weekly forecast, kept forever so the track record keeps growing.

- store/live.jsonl        forecasts made on the day, one per line, append-only
- store/backfill.jsonl.gz forecasts reconstructed for past Fridays, regenerable with `backfill`

Both use the record format of Forecast.to_record(). A live forecast wins over a
backfilled one for the same origin.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store"
LIVE = STORE / "live.jsonl"
BACKFILL = STORE / "backfill.jsonl.gz"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as fh:
        for rec in sorted(records, key=lambda r: r["origin"]):
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")


def read_records() -> list[dict]:
    """All forecasts sorted by origin; live replaces backfill on the same date."""
    by_origin = {r["origin"]: r for r in _read(BACKFILL)}
    by_origin.update({r["origin"]: r for r in _read(LIVE)})
    return [by_origin[k] for k in sorted(by_origin)]


def upsert_live(record: dict) -> None:
    records = [r for r in _read(LIVE) if r["origin"] != record["origin"]]
    _write(LIVE, records + [record])


def write_backfill(records: list[dict]) -> None:
    _write(BACKFILL, records)
