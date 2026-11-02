"""The numbers behind a weekly note, written to reports/<origin>/summary.json.

The agent that writes the news section reads this file, so every figure it
quotes comes from here rather than being recomputed by hand.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import coverage, origin_position
from .data import GOLD, TICKERS
from .model import FAN_Q, GRID_Q, HORIZONS, Forecast


def _pit_at(prev: Forecast, h: int, price: float) -> tuple[float, bool]:
    """PIT of `price` h days after the previous origin; exact on scored horizons, else from the fan."""
    if h in prev.grid:
        return float(np.interp(price, prev.grid[h], GRID_Q / 100, left=0.005, right=0.995)), True
    fan = [prev.fan[q][h - 1] for q in FAN_Q]
    return float(np.interp(price, fan, np.array(FAN_Q) / 100, left=0.005, right=0.995)), False


def build(prices: pd.DataFrame, fc: Forecast, records: list[dict], scores: pd.DataFrame) -> dict:
    gold = prices[GOLD].dropna().loc[: fc.origin]
    filled = prices.loc[: fc.origin].ffill()
    earlier = [r for r in records if pd.Timestamp(r["origin"]) < fc.origin]
    prev = Forecast.from_record(earlier[-1]) if earlier else None
    out: dict = {
        "origin": f"{fc.origin:%Y-%m-%d}",
        "spot": round(fc.spot, 2),
        "n_records": len(records),
        "n_live": sum(r["source"] == "live" for r in records),
    }

    # Context
    peak_date = gold.idxmax()
    before = gold.iloc[:-1]
    below = before[before <= fc.spot]
    year = before.loc[f"{fc.origin.year}-01-01":]
    out["context"] = {
        "peak": round(float(gold.max()), 2),
        "peak_date": f"{peak_date:%Y-%m-%d}",
        "from_peak": fc.spot / float(gold.max()) - 1,
        "lowest_close_since": f"{below.index[-1]:%Y-%m-%d}" if len(below) else None,
        "year_low_before": round(float(year.min()), 2) if len(year) else None,
        "year_low_before_date": f"{year.idxmin():%Y-%m-%d}" if len(year) else None,
        "ytd": fc.spot / float(before.loc[: f"{fc.origin.year - 1}-12-31"].iloc[-1]) - 1,
    }

    # Model this week vs last week
    f = fc.fit
    out["model"] = {
        "vol_next": f.vol_next, "vol_long_run": f.vol_long_run, "alpha": f.alpha, "beta": f.beta,
        "nu": f.nu, "persistence": f.persistence, "half_life_days": f.half_life,
        "daily_sigma": float(np.sqrt(f.var_next)),
        "prev_vol_next": prev.fit.vol_next if prev else None,
        "prev_alpha": prev.fit.alpha if prev else None,
        "prev_beta": prev.fit.beta if prev else None,
        "prev_nu": prev.fit.nu if prev else None,
    }

    # Ranges from here
    dates = pd.bdate_range(fc.origin + pd.Timedelta(days=1), periods=len(fc.fan[50]))
    out["forward"] = [
        {"h": h, "date": f"{dates[h - 1]:%Y-%m-%d}",
         **{f"q{q}": round(float(fc.fan[q][h - 1]), 2) for q in FAN_Q}}
        for h in (5, 10, 21)
    ]

    if prev is not None:
        pos0 = origin_position(gold.index, prev.origin)
        week = gold.iloc[pos0:]
        rets = np.log(week).diff().dropna()
        h = len(week) - 1
        pit, exact = _pit_at(prev, h, fc.spot) if 1 <= h <= len(prev.fan[50]) else (None, False)
        sigma = float(np.sqrt(prev.fit.var_next))
        worst = rets.idxmin() if len(rets) else None
        out["week"] = {
            "prev_origin": f"{prev.origin:%Y-%m-%d}",
            "prev_spot": round(prev.spot, 2),
            "change": fc.spot / prev.spot - 1,
            "days": [{"date": f"{d:%Y-%m-%d}", "close": round(float(v), 2),
                      "ret": float(np.expm1(rets[d])) if d in rets.index else None}
                     for d, v in week.items()],
            "trading_days": h,
        }
        if pit is not None:
            out["last_forecast"] = {
                "h": h,
                "pit": pit,
                "pit_exact": exact,
                "band90": [round(float(prev.fan[5][h - 1]), 2), round(float(prev.fan[95][h - 1]), 2)],
                "inside90": bool(prev.fan[5][h - 1] <= fc.spot <= prev.fan[95][h - 1]),
                "lowest_close": round(float(week.iloc[1:].min()), 2),
                "highest_close": round(float(week.iloc[1:].max()), 2),
                "prev_daily_sigma": sigma,
                "worst_day": f"{worst:%Y-%m-%d}" if worst is not None else None,
                "worst_day_ret": float(np.expm1(rets.min())) if len(rets) else None,
                "worst_day_x_sigma": float(abs(rets.min()) / sigma) if len(rets) else None,
            }
        cross = []
        for t, name in TICKERS.items():
            a, b = filled[t].get(prev.origin), filled[t].iloc[-1]
            if pd.isna(a) or pd.isna(b):
                continue
            change = (b - a) * 100 if t == "^TNX" else b / a - 1
            cross.append({"ticker": t, "name": name, "prev": round(float(a), 2), "now": round(float(b), 2),
                          "change": float(change), "unit": "bp" if t == "^TNX" else "pct"})
        out["cross_asset"] = cross

    cov = coverage(scores, fc.origin) if len(scores) else pd.DataFrame()
    out["coverage"] = [
        {k: (f"{v:%Y-%m-%d}" if isinstance(v, pd.Timestamp) else v) for k, v in row.items()}
        for row in cov.to_dict("records")
    ]
    return out
