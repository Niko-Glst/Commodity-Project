"""Copper and the tech market: co-movement, and whether copper leads.

Two different questions:
- Co-movement: do copper and the Nasdaq move together in the same week? (correlation)
- Leading indicator: does copper's past move help forecast the Nasdaq's next move? (out-of-sample test)

Strong co-movement does not make copper an indicator: an indicator has to be known before the move.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

COPPER, GOLD = "HG=F", "GC=F"
ERAS = {
    "Sep 2000 - 2007": ("2000-09-01", "2007-12-31"),
    "Crisis 2008-09": ("2008-01-01", "2009-12-31"),
    "2010-2019": ("2010-01-01", "2019-12-31"),
    "2020-2022": ("2020-01-01", "2022-12-31"),
    "AI era, 2023-": ("2023-01-01", None),
}

# ---------------------------------------------------------------- pre-registered test (fixed 19 Nov 2026)
# Copper counts as a leading indicator for the Nasdaq only if a candidate signal, used in an expanding
# regression refitted every week, forecasts the Nasdaq Composite's next 4-week log return better than the
# expanding historical mean (out-of-sample R^2 > 0), with a one-sided Clark-West p-value below 0.05 / 3
# (Bonferroni, three candidates), and with R^2 > 0 in both halves of the evaluation period.
CANDIDATES = {
    "Copper, past 4 weeks": ("copper", 4),
    "Copper, past 13 weeks": ("copper", 13),
    "Copper/gold ratio, past 13 weeks": ("ratio", 13),
}
TARGET = "^IXIC"
HORIZON = 4          # weeks ahead
BURN_IN = 260        # known (signal, outcome) pairs before the first forecast: five years of weeks
P_MAX = 0.05 / len(CANDIDATES)


# ---------------------------------------------------------------- weekly data
def weekly_closes(df: pd.DataFrame) -> pd.DataFrame:
    """Last available close of each week (weeks end on Friday), indexed by the week's last trading day."""
    periods = df.index.to_period("W-FRI")
    g = df.groupby(periods)
    out = g.last()
    out.index = pd.DatetimeIndex(g.apply(lambda x: x.index[-1]).values)
    return out


def weekly_returns(df: pd.DataFrame) -> pd.DataFrame:
    return np.log(weekly_closes(df)).diff()


def fisher_ci(r: float, n: int, level: float = 0.95) -> tuple[float, float]:
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    q = stats.norm.ppf(0.5 + level / 2)
    return float(np.tanh(z - q * se)), float(np.tanh(z + q * se))


def era_correlations(wr: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    rows = []
    for name, (start, end) in ERAS.items():
        x = wr[[a, b]].loc[start:end].dropna()
        r = float(x[a].corr(x[b]))
        lo, hi = fisher_ci(r, len(x))
        rows.append({"era": name, "n": len(x), "corr": r, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def fisher_diff(r1: float, n1: int, r2: float, n2: int) -> tuple[float, float]:
    """Two-sided test that two correlations from independent samples are equal."""
    z = (np.arctanh(r1) - np.arctanh(r2)) / np.sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
    return float(z), float(2 * stats.norm.sf(abs(z)))


# ---------------------------------------------------------------- forecasting panel
def panel(df: pd.DataFrame, target: str = TARGET, h: int = HORIZON, source: str = COPPER) -> pd.DataFrame:
    """One row per weekly origin: the target's next-h-week log return and every candidate signal.

    Signals use closes up to the trading day *before* the origin, so they cannot contain anything
    that happened after the target's close on the origin day (COMEX and Nasdaq close at different times).
    """
    cols = [target, source, GOLD] if source == COPPER else [target, source]
    d = df[list(dict.fromkeys(cols))].dropna()
    pos = pd.Series(np.arange(len(d)), index=d.index)
    origins = pos.groupby(d.index.to_period("W-FRI")).max().values           # last trading day of each week
    origins = origins[origins >= 1]
    lt = np.log(d[target].values)
    out = pd.DataFrame(index=d.index[origins])
    out["target_fwd"] = pd.Series(lt[origins]).shift(-h).values - lt[origins]
    prev = origins - 1                                                       # the day before each origin
    lx = pd.Series(np.log(d[source].values[prev]))
    signals = {"copper": lx}
    if source == COPPER:
        signals["ratio"] = lx - np.log(d[GOLD].values[prev])
    for name, s in signals.items():
        for k in (4, 13):
            out[f"{name}_{k}"] = (s - s.shift(k)).values
    return out


# ---------------------------------------------------------------- out-of-sample test
def oos(p: pd.DataFrame, signal: str, h: int = HORIZON, burn_in: int = BURN_IN) -> pd.DataFrame:
    """Expanding-window forecasts: OLS of target_fwd on the signal vs the historical mean.

    At origin w only pairs whose outcome is known by w (origin j with j + h <= w) are used.
    Rows whose own outcome is not known yet are kept (outcome NaN): they are the live forecasts.
    """
    y, x = p["target_fwd"].values, p[signal].values
    rows = []
    for w in range(len(p)):
        if np.isnan(x[w]):
            continue
        j = np.arange(0, w - h + 1)
        j = j[~np.isnan(x[j]) & ~np.isnan(y[j])]
        if len(j) < burn_in:
            continue
        xj, yj = x[j], y[j]
        b = np.cov(xj, yj, ddof=0)[0, 1] / np.var(xj)
        a = yj.mean() - b * xj.mean()
        rows.append({"origin": p.index[w], "outcome": y[w], "fc_model": a + b * x[w],
                     "fc_mean": yj.mean(), "slope": b, "signal": x[w]})
    return pd.DataFrame(rows).set_index("origin")


def newey_west_se(f: np.ndarray, lags: int) -> float:
    f = f - f.mean()
    n = len(f)
    var = f @ f / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (f[k:] @ f[:-k]) / n
    return float(np.sqrt(max(var, 1e-300) / n))


def r2_os(r: pd.DataFrame) -> float:
    return float(1 - ((r.outcome - r.fc_model) ** 2).sum() / ((r.outcome - r.fc_mean) ** 2).sum())


def evaluate(forecasts: pd.DataFrame, h: int = HORIZON) -> dict:
    """Out-of-sample R^2, Clark-West test (one-sided, Newey-West with h-1 lags) and the two halves."""
    r = forecasts.dropna(subset=["outcome"])
    e_m, e_b = r.outcome - r.fc_model, r.outcome - r.fc_mean
    f = (e_b ** 2 - (e_m ** 2 - (r.fc_mean - r.fc_model) ** 2)).values
    t = float(f.mean() / newey_west_se(f, max(h - 1, 0)))
    mid = r.index[len(r) // 2]
    early, late = r.loc[r.index < mid], r.loc[r.index >= mid]
    hit = float((np.sign(r.fc_model - r.fc_mean) == np.sign(r.outcome - r.fc_mean)).mean())
    return {"n": len(r), "first": r.index[0], "last": r.index[-1], "r2_os": r2_os(r), "cw_t": t,
            "cw_p": float(stats.norm.sf(t)), "r2_early": r2_os(early), "r2_late": r2_os(late), "split": mid,
            "slope_last": float(forecasts.slope.iloc[-1]), "hit_rate": hit}


def qualifies(res: dict, p_max: float = P_MAX) -> bool:
    return bool(res["r2_os"] > 0 and res["cw_p"] < p_max and res["r2_early"] > 0 and res["r2_late"] > 0)


def preregistered(df: pd.DataFrame) -> pd.DataFrame:
    """The three pre-registered candidates against the Nasdaq Composite, 4 weeks ahead."""
    p = panel(df)
    rows = []
    for name, (kind, k) in CANDIDATES.items():
        fc = oos(p, f"{kind}_{k}")
        res = evaluate(fc)
        live = fc[fc.outcome.isna()]
        rows.append({"candidate": name, **res, "qualifies": qualifies(res),
                     "live_origin": live.index[-1] if len(live) else None,
                     "live_signal": float(live.signal.iloc[-1]) if len(live) else None,
                     "live_model": float(live.fc_model.iloc[-1]) if len(live) else None,
                     "live_mean": float(live.fc_mean.iloc[-1]) if len(live) else None})
    return pd.DataFrame(rows)
