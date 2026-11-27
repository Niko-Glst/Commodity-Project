"""Futures rolls in the continuous COMEX series (added 27 Nov 2026).

Yahoo's GC=F switches from the expiring contract to the next one. On the switch day the series jumps by the
spread between the two contracts (on 26 Nov 2026 about $29, +0.8%), which is not a price move. A forecast made on
the old contract must be scored on the old contract: outcomes after a roll are multiplied by the old/new price
ratio on the last day both were in the series. Rolls are listed in rolls.json with how each date was found.

score() in backtest.py stays a pure function: callers pass `load_rolls()` explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROLLS_FILE = Path(__file__).with_name("rolls.json")


def load_rolls(path: Path = ROLLS_FILE, include_unverified: bool = False) -> list[dict]:
    """Rolls from rolls.json. Entries marked "verified": false are skipped unless asked for, so an unconfirmed
    roll date never changes a score."""
    rolls = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return [r for r in rolls if include_unverified or r.get("verified", True)]


def crossed(origin, outcome_date, rolls: list[dict] | None) -> list[dict]:
    """Rolls that fall after the origin and on or before the outcome date."""
    o, t = pd.Timestamp(origin), pd.Timestamp(outcome_date)
    return [r for r in (rolls or []) if o < pd.Timestamp(r["date"]) <= t]


def outcome_factor(origin, outcome_date, rolls: list[dict] | None) -> float:
    """Multiply an outcome by this to express it in the contract the forecast was made on."""
    f = 1.0
    for r in crossed(origin, outcome_date, rolls):
        f *= float(r["ratio"])
    return f
