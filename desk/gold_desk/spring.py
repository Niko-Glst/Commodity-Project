"""Spring tests: does gold snap back harder the further it is stretched from its 'value'?

Pre-registered on 23 Nov 2026, before any result on real data was computed. The rules and constants
below are fixed; the commit that adds this file comes before the first run.

The idea (the user's, 23 Nov 2026): price moves around a true value like a mass on a spring. The
further it is stretched, the harder the pull back, so very large moves are followed by sharp moves the
other way. The desk model (GARCH(1,1), Student-t, zero drift) already makes big moves follow big moves,
but in a random direction. A spring adds a predictable direction: a pull back toward value.

Stretch at origin t, using only closes up to t:
    s_t = ln(P_t / SMA_n(t)) / sigma_t
with sigma_t the model's own next-day sigma at that origin (square root of the stored var_next) and
n = 50 ('fast value') or 200 ('slow value') trading days.
Standardised forward return:  z_t,h = ln(P_t+h / P_t) / (sigma_t * sqrt(h)).

H4  A spring exists: OLS of z_t,5 on s_t has a negative slope; one-sided p < 0.05/2 (Bonferroni over
    the two anchors; Newey-West with 1 lag; weekly origins make 5-day outcomes non-overlapping), and
    the slope is negative in both halves (origins before 2016 and from 2016).
H5  The spring stiffens with the stretch: in z_t,5 = a + b s_t + c s_t|s_t|, c < 0 with one-sided
    p < 0.05/2, per anchor.
H6  The gate into the model: a drift that shifts the stored zero-drift forecast by
    b_h(t) * s_t * sigma_t * sqrt(h), where b_h(t) is the slope of z_h on s estimated only on origins
    whose h-day outcome was known at t (expanding, after SPRING_BURN_IN origins), must pass the drift
    rule: 1-month quantile score better with two-sided p < 0.05/2, better in both halves, and the
    1-week score not worse. Only an anchor that passes H6 may enter the live forecast; the others run
    as a shadow in the note.

Descriptive only (no test, no effect on the forecast): what followed days with 3-sigma moves, and a
state-space fit of log gold as a random-walk value plus an AR(1) stretch (a discrete version of
Schwartz and Smith 2000), which gives the spring's half-life.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .backtest import SPLIT, diebold_mariano, origin_position, quantile_loss
from .drivers import _hac

SPRING_ANCHORS = (50, 200)          # trading days behind the moving-average 'value'
SPRING_P = 0.05 / len(SPRING_ANCHORS)
SPRING_BURN_IN = 260                # weekly origins (about 5 years) before an H6 slope is used
EVENT_SIGMA = 3.0                   # descriptive: a big day is a close-to-close move of 3 sigma or more
EVENT_VOL_WINDOW = 63               # past trading days behind the event sigma


def stretch_panel(records: list[dict], gold: pd.Series, anchors=SPRING_ANCHORS,
                  horizons=(5, 21)) -> pd.DataFrame:
    """One row per forecast origin: the model's sigma, the stretch per anchor, standardised forward returns."""
    lg = np.log(gold)
    sma = {n: gold.rolling(n).mean() for n in anchors}
    rows = []
    for rec in records:
        origin = pd.Timestamp(rec["origin"])
        pos = origin_position(gold.index, origin)
        if pos is None:
            continue
        sig = float(np.sqrt(rec["fit"]["var_next"]))
        row = {"origin": origin, "pos": pos, "spot": float(gold.iloc[pos]), "sigma": sig}
        for n in anchors:
            m = sma[n].iloc[pos]
            row[f"s{n}"] = float(np.log(gold.iloc[pos] / m) / sig) if np.isfinite(m) else np.nan
        for h in horizons:
            row[f"z{h}"] = (float((lg.iloc[pos + h] - lg.iloc[pos]) / (sig * np.sqrt(h)))
                            if pos + h < len(gold) else np.nan)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("origin").reset_index(drop=True)


def slope_test(panel: pd.DataFrame, anchor: int, h: int = 5, lags: int = 1, stiff: bool = False) -> dict:
    """OLS of z_h on the stretch (and s|s| if stiff), Newey-West errors; the coefficient tested is the
    slope (H4) or the s|s| term (H5). One-sided p for 'coefficient < 0'."""
    d = panel.dropna(subset=[f"s{anchor}", f"z{h}"])
    s, y = d[f"s{anchor}"].to_numpy(), d[f"z{h}"].to_numpy()
    X = np.column_stack([np.ones_like(s), s] + ([s * np.abs(s)] if stiff else []))
    k = 2 if stiff else 1
    b, se = _hac(X, y, lags)
    t = b[k] / se[k]
    out = {"anchor": anchor, "h": h, "n": len(d), "coef": float(b[k]), "t": float(t),
           "p_one_sided": float(stats.norm.cdf(t)), "intercept": float(b[0])}
    if stiff:
        out["slope"] = float(b[1])
    early = (d["origin"] < SPLIT).to_numpy()
    for name, mask in (("early", early), ("late", ~early)):
        bb, _ = _hac(X[mask], y[mask], lags)
        out[f"coef_{name}"] = float(bb[k])
    return out


def h4(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n in SPRING_ANCHORS:
        r = slope_test(panel, n, h=5, lags=1)
        r["passed"] = bool(r["p_one_sided"] < SPRING_P and r["coef"] < 0 and r["coef_early"] < 0 and r["coef_late"] < 0)
        r21 = slope_test(panel, n, h=21, lags=4)          # descriptive: the 1-month slope
        r.update({"coef_21": r21["coef"], "t_21": r21["t"]})
        rows.append(r)
    return pd.DataFrame(rows)


def h5(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n in SPRING_ANCHORS:
        r = slope_test(panel, n, h=5, lags=1, stiff=True)
        r["passed"] = bool(r["p_one_sided"] < SPRING_P and r["coef"] < 0)
        rows.append(r)
    return pd.DataFrame(rows)


def past_slope(panel: pd.DataFrame, anchor: int, h: int, pos: int, burn_in: int = SPRING_BURN_IN) -> float | None:
    """Slope of z_h on s from origins whose h-day outcome was known at trading-day position pos."""
    past = panel[(panel["pos"] + h <= pos)].dropna(subset=[f"s{anchor}", f"z{h}"])
    if len(past) < burn_in:
        return None
    s = past[f"s{anchor}"].to_numpy()
    X = np.column_stack([np.ones_like(s), s])
    return float(np.linalg.lstsq(X, past[f"z{h}"].to_numpy(), rcond=None)[0][1])


def spring_shift(slope: float, stretch: float, sigma: float, h: int) -> float:
    """Shift of the log-return distribution h days ahead implied by the spring."""
    return float(slope * stretch * sigma * np.sqrt(h))


def spring_check(records: list[dict], gold: pd.Series, panel: pd.DataFrame, anchor: int,
                 burn_in: int = SPRING_BURN_IN) -> pd.DataFrame:
    """H6: re-score the stored zero-drift forecasts with the spring shift (no refitting needed)."""
    by_origin = {pd.Timestamp(r["origin"]): r for r in records}
    d = panel.dropna(subset=[f"s{anchor}"])
    rows = []
    for h, lags in ((5, 1), (21, 5)):     # weekly origins: 21-day windows overlap about 4 weeks
        out = []
        for _, row in d.iterrows():
            pos = int(row["pos"])
            if pos + h >= len(gold):
                continue
            b = past_slope(panel, anchor, h, pos, burn_in)
            if b is None:
                continue
            rec = by_origin[row["origin"]]
            r = float(np.log(gold.iloc[pos + h] / rec["spot"]))
            q0 = np.log(np.asarray(rec["grid"][str(h)]) / rec["spot"])
            q1 = q0 + spring_shift(b, row[f"s{anchor}"], row["sigma"], h)
            out.append((row["origin"], quantile_loss(r, q0), quantile_loss(r, q1), b))
        df = pd.DataFrame(out, columns=["origin", "l0", "l1", "b"])
        diff = (df["l1"] - df["l0"]).to_numpy()
        early, late = df["origin"] < SPLIT, df["origin"] >= SPLIT
        t, p = diebold_mariano(diff, lags)
        rows.append({"anchor": anchor, "h": h, "n": len(df), "first": df["origin"].min(),
                     "change": diff.mean() / df["l0"].mean(), "t": t, "p": p,
                     "change_early": diff[early].mean() / df.loc[early, "l0"].mean() if early.any() else np.nan,
                     "change_late": diff[late].mean() / df.loc[late, "l0"].mean() if late.any() else np.nan,
                     "slope_last": float(df["b"].iloc[-1]) if len(df) else np.nan})
    return pd.DataFrame(rows)


def spring_qualifies(check: pd.DataFrame, p_max: float = SPRING_P) -> bool:
    """The switch rule, fixed before the first run (23 Nov 2026), same shape as the drift rule."""
    m, w = check.set_index("h").loc[21], check.set_index("h").loc[5]
    return bool(m["p"] < p_max and m["change"] < 0 and m["change_early"] < 0 and m["change_late"] < 0
                and w["change"] <= 0)


# ------------------------------------------------------------------ descriptive

def big_moves(gold: pd.Series, k: float = EVENT_SIGMA, window: int = EVENT_VOL_WINDOW,
              after=(1, 5, 21)) -> pd.DataFrame:
    """Days with a close-to-close move of k sigma or more (sigma from the previous `window` days only)
    and what followed, in the same sigma units."""
    r = np.log(gold).diff()
    sig = r.rolling(window).std().shift(1)
    z = r / sig
    rows = []
    for d in z.index[z.abs() >= k]:
        pos = gold.index.get_loc(d)
        row = {"date": d, "ret": float(r[d]), "z": float(z[d]), "sigma": float(sig[d])}
        for h in after:
            if pos + h < len(gold):
                fr = float(np.log(gold.iloc[pos + h] / gold.iloc[pos]))
                row[f"r{h}"], row[f"z{h}"] = fr, fr / (sig[d] * np.sqrt(h))
        rows.append(row)
    return pd.DataFrame(rows)


def summarise_moves(ev: pd.DataFrame, gold: pd.Series, window: int = EVENT_VOL_WINDOW, after=(1, 5, 21)) -> pd.DataFrame:
    """Average follow-through after big falls and big rallies, against all days."""
    r = np.log(gold).diff()
    sig = r.rolling(window).std().shift(1)
    base = {}
    for h in after:
        fr = np.log(gold.shift(-h) / gold)
        base[h] = (fr / (sig * np.sqrt(h))).dropna()
    rows = []
    for name, sel in (("Falls of 3 sigma or more", ev["z"] < 0), ("Rallies of 3 sigma or more", ev["z"] > 0)):
        e = ev[sel]
        row = {"group": name, "n": int(len(e))}
        for h in after:
            col = e[f"z{h}"].dropna()
            row[f"mean_z{h}"] = float(col.mean())
            row[f"up{h}"] = float((col > 0).mean())
            row[f"abs_z{h}"] = float(col.abs().mean())
        rows.append(row)
    row = {"group": "All days", "n": int(len(base[1]))}
    for h in after:
        row[f"mean_z{h}"] = float(base[h].mean())
        row[f"up{h}"] = float((base[h] > 0).mean())
        row[f"abs_z{h}"] = float(base[h].abs().mean())
    rows.append(row)
    return pd.DataFrame(rows)


def state_space(gold: pd.Series, start: str = "2006-01-01") -> dict:
    """Weekly log gold = random-walk value + AR(1) stretch (Kalman filter, Gaussian, in-sample fit).
    Returns the AR coefficient, the stretch half-life in weeks and the filtered stretch and value."""
    import statsmodels.api as sm
    y = np.log(gold.loc[start:].resample("W-FRI").last().dropna()) * 100
    res = sm.tsa.UnobservedComponents(y, level="rwalk", autoregressive=1).fit(disp=False)
    phi = float(res.params["ar.L1"])
    stretch = pd.Series(res.autoregressive["filtered"], index=y.index) / 100
    value = pd.Series(res.level["filtered"], index=y.index) / 100
    return {"phi": phi, "half_life_weeks": float(np.log(0.5) / np.log(phi)) if 0 < phi < 1 else float("nan"),
            "sigma_value": float(np.sqrt(res.params["sigma2.level"])) / 100,
            "sigma_stretch": float(np.sqrt(res.params["sigma2.ar"])) / 100,
            "stretch": stretch, "value": value, "llf": float(res.llf)}
