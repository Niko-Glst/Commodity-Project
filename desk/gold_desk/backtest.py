"""Score every stored forecast against the closes that followed it.

For each forecast and each scored horizon h, the realised close h trading days
after the origin gets a PIT value (its percentile in the forecast distribution)
and a hit/miss for the 90% range. If the model is calibrated, 90% of closes land
inside the range, 5% below it and 5% above it, and the PIT values are uniform.

Weekly origins make the 1-day and 5-day scores non-overlapping. The 10- and
21-day windows overlap, so their Kupiec p-values are too optimistic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .model import GRID_Q, HORIZONS


def origin_position(index: pd.DatetimeIndex, origin: pd.Timestamp) -> int | None:
    pos = index.searchsorted(origin, side="right") - 1
    return int(pos) if pos >= 0 and index[pos] == origin else None


def score(records: list[dict], gold: pd.Series) -> pd.DataFrame:
    rows = []
    for rec in records:
        origin = pd.Timestamp(rec["origin"])
        pos = origin_position(gold.index, origin)
        if pos is None:
            continue
        for h in HORIZONS:
            if pos + h >= len(gold):
                continue
            realised = float(gold.iloc[pos + h])
            grid = np.asarray(rec["grid"][str(h)])
            rows.append({
                "origin": origin,
                "source": rec["source"],
                "h": h,
                "spot": rec["spot"],
                "realised": realised,
                "ret": realised / rec["spot"] - 1,
                "q5": grid[4],
                "q95": grid[94],
                "pit": float(np.interp(realised, grid, GRID_Q / 100, left=0.005, right=0.995)),
                "below5": realised < grid[4],
                "above95": realised > grid[94],
            })
    df = pd.DataFrame(rows)
    if len(df):
        df["inside90"] = ~(df["below5"] | df["above95"])
    return df


def kupiec(n: int, misses: int, p: float) -> float:
    """Kupiec POF test: p-value for 'the miss rate equals p'."""
    if n == 0:
        return float("nan")
    phat = misses / n

    def loglik(q: float) -> float:
        out = 0.0
        if misses:
            out += misses * np.log(q)
        if n - misses:
            out += (n - misses) * np.log(1 - q)
        return out

    lr = -2 * (loglik(p) - loglik(phat))
    return float(1 - stats.chi2.cdf(lr, 1))


def coverage(scores: pd.DataFrame, last_origin: pd.Timestamp) -> pd.DataFrame:
    """Hit rates per horizon for all history, the last 52 weeks and live forecasts only."""
    windows = {
        "All history": scores,
        "Last 52 weeks": scores[scores["origin"] > last_origin - pd.Timedelta(weeks=52)],
        "Live only": scores[scores["source"] == "live"],
    }
    rows = []
    for name, df in windows.items():
        for h in HORIZONS:
            sub = df[df["h"] == h]
            n = len(sub)
            misses = int((~sub["inside90"]).sum()) if n else 0
            rows.append({
                "window": name,
                "h": h,
                "n": n,
                "first": sub["origin"].min() if n else None,
                "inside90": sub["inside90"].mean() if n else float("nan"),
                "below5": sub["below5"].mean() if n else float("nan"),
                "above95": sub["above95"].mean() if n else float("nan"),
                "kupiec_p": kupiec(n, misses, 0.10),
            })
    return pd.DataFrame(rows)
