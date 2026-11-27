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
from .rolls import crossed, outcome_factor


def origin_position(index: pd.DatetimeIndex, origin: pd.Timestamp) -> int | None:
    pos = index.searchsorted(origin, side="right") - 1
    return int(pos) if pos >= 0 and index[pos] == origin else None


def score(records: list[dict], gold: pd.Series, rolls: list[dict] | None = None) -> pd.DataFrame:
    """rolls=None (default) scores on the continuous series as before; pass rolls.load_rolls() so an outcome after
    a futures roll is expressed in the contract the forecast was made on."""
    rows = []
    for rec in records:
        origin = pd.Timestamp(rec["origin"])
        pos = origin_position(gold.index, origin)
        if pos is None:
            continue
        for h in HORIZONS:
            if pos + h >= len(gold):
                continue
            when = gold.index[pos + h]
            realised = float(gold.iloc[pos + h]) * outcome_factor(origin, when, rolls)
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
                "roll_adjusted": bool(crossed(origin, when, rolls)),
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


SHADOW_SHRINK = 0.5         # shadow drift: half the expanding mean of daily log returns
SPLIT = pd.Timestamp("2016-01-01")


def quantile_loss(realised: float, quantiles: np.ndarray) -> float:
    """Pinball loss averaged over the percentile grid; approximates the CRPS. Lower is better."""
    return float(np.mean((GRID_Q / 100 - (realised < quantiles)) * (realised - quantiles)))


def diebold_mariano(diff: np.ndarray, lags: int) -> tuple[float, float]:
    """t-statistic and two-sided p-value for 'mean loss difference is zero', Newey-West variance."""
    n = len(diff)
    e = diff - diff.mean()
    var = e @ e / n + 2 * sum((1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n for k in range(1, lags + 1))
    if n < 10 or var <= 0:
        return float("nan"), float("nan")
    t = diff.mean() / np.sqrt(var / n)
    return float(t), float(2 * (1 - stats.norm.cdf(abs(t))))


def drift_check(records: list[dict], gold: pd.Series, shrink: float = SHADOW_SHRINK) -> pd.DataFrame:
    """Shadow test: would a drift of `shrink` x the expanding mean have scored better than zero drift?

    Drift is a pure shift of the log-return distribution by mu * h, so the stored
    zero-drift forecasts can be re-scored without refitting. mu uses only returns
    up to each forecast's own origin.
    """
    mean_to_date = np.log(gold).diff().expanding().mean()
    rows = []
    for h, lags in ((5, 1), (21, 5)):     # weekly origins: 21-day windows overlap about 4 weeks
        out = []
        for rec in records:
            pos = origin_position(gold.index, pd.Timestamp(rec["origin"]))
            if pos is None or pos + h >= len(gold):
                continue
            r = float(np.log(gold.iloc[pos + h] / rec["spot"]))
            q0 = np.log(np.asarray(rec["grid"][str(h)]) / rec["spot"])
            q1 = q0 + shrink * mean_to_date.iloc[pos] * h
            out.append((pd.Timestamp(rec["origin"]), quantile_loss(r, q0), quantile_loss(r, q1),
                        r < q0[4], r > q0[94], r < q1[4], r > q1[94]))
        df = pd.DataFrame(out, columns=["origin", "l0", "l1", "b0", "a0", "b1", "a1"])
        diff = (df["l1"] - df["l0"]).to_numpy()
        early, late = df["origin"] < SPLIT, df["origin"] >= SPLIT
        t, p = diebold_mariano(diff, lags)
        rows.append({
            "h": h, "n": len(df),
            "change": diff.mean() / df["l0"].mean(), "t": t, "p": p,
            "change_early": diff[early].mean() / df.loc[early, "l0"].mean(),
            "change_late": diff[late].mean() / df.loc[late, "l0"].mean(),
            "below_zero": df["b0"].mean(), "above_zero": df["a0"].mean(),
            "below_drift": df["b1"].mean(), "above_drift": df["a1"].mean(),
        })
    return pd.DataFrame(rows)


def drift_qualifies(check: pd.DataFrame) -> bool:
    """The switch rule, fixed before the first test: drift goes in only if it significantly
    improves the 1-month score, improves it in both halves of the sample, and does not
    worsen the 1-week score."""
    m, w = check.set_index("h").loc[21], check.set_index("h").loc[5]
    return bool(m["p"] < 0.05 and m["change"] < 0 and m["change_early"] < 0 and m["change_late"] < 0
                and w["change"] <= 0)


WINDOW_CANDIDATES = {"10 years": 2520, "5 years": 1260}   # trading days of returns
WINDOW_P = 0.05 / len(WINDOW_CANDIDATES)                   # Bonferroni over the candidates


def window_check(base: list[dict], rolling: list[dict], gold: pd.Series) -> pd.DataFrame:
    """Rolling-sample forecasts against the expanding-sample forecasts, on the same origins.

    Both sets use the same seed, so the comparison runs on common random numbers.
    Scores are quantile losses of the log return; `change` < 0 means the rolling
    sample scored better. The two halves split the shared origins at their median.
    """
    by_origin = {r["origin"]: r for r in base}
    rows = []
    for h, lags in ((5, 1), (21, 5)):
        out = []
        for rec in rolling:
            ref = by_origin.get(rec["origin"])
            pos = origin_position(gold.index, pd.Timestamp(rec["origin"]))
            if ref is None or pos is None or pos + h >= len(gold):
                continue
            r = float(np.log(gold.iloc[pos + h] / rec["spot"]))
            q0 = np.log(np.asarray(ref["grid"][str(h)]) / ref["spot"])
            q1 = np.log(np.asarray(rec["grid"][str(h)]) / rec["spot"])
            out.append((pd.Timestamp(rec["origin"]), quantile_loss(r, q0), quantile_loss(r, q1),
                        not (q0[4] <= r <= q0[94]), not (q1[4] <= r <= q1[94])))
        df = pd.DataFrame(out, columns=["origin", "l0", "l1", "m0", "m1"])
        diff = (df["l1"] - df["l0"]).to_numpy()
        early = (df["origin"] < df["origin"].median()).to_numpy()
        t, p = diebold_mariano(diff, lags)
        rows.append({
            "h": h, "n": len(df), "first": df["origin"].min(),
            "change": diff.mean() / df["l0"].mean(), "t": t, "p": p,
            "change_early": diff[early].mean() / df.loc[early, "l0"].mean(),
            "change_late": diff[~early].mean() / df.loc[~early, "l0"].mean(),
            "inside90_expanding": 1 - df["m0"].mean(), "inside90_rolling": 1 - df["m1"].mean(),
        })
    return pd.DataFrame(rows)


def window_qualifies(check: pd.DataFrame, p_max: float = WINDOW_P) -> bool:
    """The switch rule, fixed before the first test (16 Nov 2026), same shape as the drift rule:
    a rolling sample replaces the expanding one only if it improves the 1-month score with
    p below the Bonferroni level, improves it in both halves, and does not worsen the
    1-week score."""
    m, w = check.set_index("h").loc[21], check.set_index("h").loc[5]
    return bool(m["p"] < p_max and m["change"] < 0 and m["change_early"] < 0 and m["change_late"] < 0
                and w["change"] <= 0)


IV_CANDIDATES = ("GVZ, bias-corrected", "Blend: half GARCH, half GVZ")
IV_P = 0.05 / len(IV_CANDIDATES)        # Bonferroni over the candidates
IV_LAG_DAYS = 1                         # use the GVZ close of the day before the origin (see iv_targets)
IV_MIN_HISTORY = 252                    # days of realised/implied ratios before the bias correction is trusted


def garch_vol_21(fit: dict, h: int = 21) -> float:
    """Annualised average volatility the GARCH fit expects over the next h days."""
    pers = fit["alpha"] + fit["beta"]
    if pers >= 1:
        return float(np.sqrt(fit["var_next"] * 252))
    long_run = fit["omega"] / (1 - pers)
    path = long_run + pers ** np.arange(h) * (fit["var_next"] - long_run)
    return float(np.sqrt(path.mean() * 252))


def iv_targets(gold: pd.Series, gvz: pd.Series) -> pd.DataFrame:
    """Per gold trading day: GVZ of the previous day, and the bias correction known on that day.

    GVZ closes at 16:15 ET, after the COMEX settlement (13:30 ET) that the model uses, so the
    same-day value would peek about three hours ahead. The previous day's close avoids that.
    Implied vol carries a risk premium: it usually sits above the vol that follows. The
    correction is the median ratio of realised 21-day vol to the GVZ that preceded it, over
    all ratios already complete on the day (each needs 21 days after its start), so it uses
    no future data.
    """
    r = np.log(gold).diff()
    iv = gvz.reindex(gold.index).ffill().shift(IV_LAG_DAYS) / 100
    realised_fwd = np.sqrt((r**2).rolling(21).mean().shift(-21) * 252)
    ratio = realised_fwd / iv
    known = ratio.shift(21)                       # the ratio starting on day s is known on day s + 21
    correction = known.expanding(min_periods=IV_MIN_HISTORY).median()
    return pd.DataFrame({"iv": iv, "correction": correction, "iv_corrected": iv * correction})


def iv_scale(rec: dict, targets: pd.DataFrame, candidate: str) -> float | None:
    """Factor on the zero-drift log returns that moves the GARCH 1-month vol to the candidate's target.

    Scaling the log returns by k is the same GARCH path with omega and the starting variance
    multiplied by k squared; tails and volatility dynamics are kept.
    """
    row = targets.loc[pd.Timestamp(rec["origin"])] if pd.Timestamp(rec["origin"]) in targets.index else None
    if row is None or pd.isna(row["iv_corrected"]):
        return None
    garch = garch_vol_21(rec["fit"])
    target = row["iv_corrected"] if candidate == IV_CANDIDATES[0] else 0.5 * (garch + row["iv_corrected"])
    return float(target / garch)


def iv_check(records: list[dict], gold: pd.Series, gvz: pd.Series) -> pd.DataFrame:
    """Score GVZ-based volatility against the plain GARCH forecasts, on the same stored forecasts.

    A scaled forecast's quantiles follow exactly from the stored ones: the log-return quantiles
    are multiplied by k, so nothing is re-simulated.
    """
    targets = iv_targets(gold, gvz)
    rows = []
    for cand in IV_CANDIDATES:
        for h, lags in ((5, 1), (21, 5)):
            out = []
            for rec in records:
                pos = origin_position(gold.index, pd.Timestamp(rec["origin"]))
                if pos is None or pos + h >= len(gold):
                    continue
                k = iv_scale(rec, targets, cand)
                if k is None:
                    continue
                r = float(np.log(gold.iloc[pos + h] / rec["spot"]))
                q0 = np.log(np.asarray(rec["grid"][str(h)]) / rec["spot"])
                q1 = k * q0
                out.append((pd.Timestamp(rec["origin"]), quantile_loss(r, q0), quantile_loss(r, q1),
                            not (q0[4] <= r <= q0[94]), not (q1[4] <= r <= q1[94]), r < q1[4], r > q1[94], k))
            df = pd.DataFrame(out, columns=["origin", "l0", "l1", "m0", "m1", "b1", "a1", "k"])
            diff = (df["l1"] - df["l0"]).to_numpy()
            early = (df["origin"] < df["origin"].median()).to_numpy()
            t, p = diebold_mariano(diff, lags)
            rows.append({
                "candidate": cand, "h": h, "n": len(df), "first": df["origin"].min(),
                "change": diff.mean() / df["l0"].mean(), "t": t, "p": p,
                "change_early": diff[early].mean() / df.loc[early, "l0"].mean(),
                "change_late": diff[~early].mean() / df.loc[~early, "l0"].mean(),
                "inside90_garch": 1 - df["m0"].mean(), "inside90_iv": 1 - df["m1"].mean(),
                "below5_iv": df["b1"].mean(), "above95_iv": df["a1"].mean(),
                "scale_median": df["k"].median(),
            })
    return pd.DataFrame(rows)


def iv_qualifies(check: pd.DataFrame, candidate: str, p_max: float = IV_P) -> bool:
    """The switch rule, fixed before the first test (17 Nov 2026), same shape as the drift and
    window rules: a GVZ candidate goes in only if it improves the 1-month score with p below
    the Bonferroni level, improves it in both halves, and does not worsen the 1-week score."""
    c = check[check["candidate"] == candidate].set_index("h")
    m, w = c.loc[21], c.loc[5]
    return bool(m["p"] < p_max and m["change"] < 0 and m["change_early"] < 0 and m["change_late"] < 0
                and w["change"] <= 0)


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
