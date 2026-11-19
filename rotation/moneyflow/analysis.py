"""Relative performance against cash, the profit-taking test, and positioning changes."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .data import CASH, COT, UNIVERSE

PEAK = "2026-10-06"          # Nasdaq Composite and S&P 500 closing highs
MOMENTUM_START = "2025-10-06"  # profit-taking test: the 12 months up to the peak (fixed before computing it)


def ret(p: pd.DataFrame, start: str, end: str | None = None) -> pd.Series:
    """Total return from the close on (or before) `start` to the close on (or before) `end`."""
    a = p.loc[:start].ffill().iloc[-1]
    b = (p.loc[:end] if end else p).ffill().iloc[-1]
    return b / a - 1


def performance(p: pd.DataFrame) -> pd.DataFrame:
    last = p.index[-1]
    out = pd.DataFrame({
        "name": [UNIVERSE[t][0] for t in p.columns], "group": [UNIVERSE[t][1] for t in p.columns],
        "since_peak": ret(p, PEAK), "november": ret(p, "2026-10-30"),
        "last_week": ret(p, f"{last - pd.Timedelta(days=7):%Y-%m-%d}"),
        "year_to_peak": ret(p, MOMENTUM_START, PEAK),
    }, index=p.columns)
    for c in ("since_peak", "november", "last_week"):
        out[c + "_vs_cash"] = out[c] - out.loc[CASH, c]
    return out


def profit_taking(perf: pd.DataFrame) -> dict:
    """Did last year's winners fall hardest? Rank correlation across the universe, cash excluded."""
    x = perf.drop(index=CASH)
    rho, p = stats.spearmanr(x.year_to_peak, x.since_peak)
    slope, intercept = np.polyfit(x.year_to_peak, x.since_peak, 1)
    top = x.nlargest(5, "year_to_peak")
    rest = x.drop(index=top.index)
    return {"spearman": float(rho), "p": float(p), "n": len(x), "slope": float(slope), "intercept": float(intercept),
            "top5": list(top.index), "top5_since_peak": float(top.since_peak.mean()),
            "rest_since_peak": float(rest.since_peak.mean())}


def beat_cash(perf: pd.DataFrame, col: str = "since_peak") -> tuple[int, int]:
    x = perf.drop(index=CASH)
    return int((x[col] > perf.loc[CASH, col]).sum()), len(x)


def positioning(c: pd.DataFrame) -> pd.DataFrame:
    """Latest net position per COT series, its change over 1 and 4 weeks, and where it sits in its range since 2024."""
    rows = []
    for name, spec in COT.items():
        s = c[name].dropna()
        oi = c[name + " | OI"].dropna()
        rng = (s.iloc[-1] - s.min()) / (s.max() - s.min())
        rows.append({"series": name, "group": spec[4], "date": s.index[-1], "net": s.iloc[-1],
                     "chg_1w": s.iloc[-1] - s.iloc[-2], "chg_4w": s.iloc[-1] - s.iloc[-5],
                     "net_pct_oi": s.iloc[-1] / oi.iloc[-1], "range_pct": rng})
    return pd.DataFrame(rows)
