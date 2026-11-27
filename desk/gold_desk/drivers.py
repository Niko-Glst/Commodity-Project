"""What moves gold: a driver attribution, and tests of three claims from the In Gold We Trust report 2026.

The GARCH model sizes moves; it says nothing about why gold moved. This module explains moves after the
fact (attribution) and tests whether any driver *predicts* the next move. Explaining and predicting are
different questions: a driver can explain most of a week's move and still be useless for the next one.

Pre-registered rules (fixed 21 Nov 2026, committed before the first run on real data):

H1  Decoupling from real yields (IGWT 2026, p. 30: "Gold is decoupling from the old drivers of real
    interest rates"). Weekly gold log return on the weekly change in the 10-year TIPS yield. Confirmed if
    the slope from March 2022 is less negative than in 2010-2021 with a one-sided p < 0.05 (HAC, 4 lags).
H2  Procyclical ETF flows (IGWT 2026, p. 21: "Western ETF investors sell procyclically"). Weekly GLD flow
    (% of assets) on gold's log return over the previous four weeks. Confirmed if the slope is positive
    with p < 0.05 (HAC, 4 lags).
H3  Positioning and flows as predictors. Three candidates for gold's log return over the next four weeks,
    each known before the origin's settlement: (a) managed-money net long as a share of open interest,
    (b) its four-week change, (c) GLD flows over the previous four weeks as a share of assets. Expanding
    OLS refitted weekly, first forecast after 156 known pairs, benchmark the historical mean. A candidate
    passes only with out-of-sample R^2 > 0, a one-sided Clark-West p < 0.05 / 3 (Newey-West, 3 lags) and
    R^2 > 0 in both halves.
Descriptive only (no rule): the attribution, and an event study of stress sell-offs (weeks with the VIX
at 30 or more and gold down 4% or more), whose sample is too small for a test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

FACTORS = {"d_real": "Real yield (10y TIPS)", "d_be": "Inflation expectations (10y breakeven)",
           "r_dxy": "US dollar", "d_vix": "Risk and stress (VIX)", "r_spx": "US stocks", "r_oil": "Oil",
           "d_mm": "Speculative positioning", "flow": "ETF flows"}
# Factors for the attribution shown in the Nova Gold Weekly (27 Nov 2026): market prices only. ETF flows and
# managed-money positioning are left out because both follow the price (H2 for flows; managed money is trend-
# following), so as regressors they are endogenous and bias the other betas.
MARKET_FACTORS = ["d_real", "d_be", "r_dxy", "d_vix", "r_spx", "r_oil"]
ATTR_WINDOW = 156                       # weeks of past data behind each week's betas (3 years)
DECOUPLE_BEFORE = ("2010-01-01", "2021-12-31")
DECOUPLE_AFTER = "2022-03-01"           # reserve freeze after the invasion of Ukraine
H3_CANDIDATES = {"mm_level": "Managed-money net long, share of open interest",
                 "mm_chg4": "Change in that share over four weeks",
                 "flow4": "GLD flows over four weeks, share of assets"}
H3_HORIZON, H3_BURN_IN = 4, 156
H3_P = 0.05 / len(H3_CANDIDATES)


# ------------------------------------------------------------------ panel
def weekly_panel(daily: pd.DataFrame, gld: pd.DataFrame | None = None, cot: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per week (last trading day, weeks end Friday).

    daily: columns gold, real, be, dxy, vix, spx, oil (levels; yields in %).
    gld:   daily columns nav, shares (State Street NAV history).
    cot:   columns mm_net, oi indexed by the Tuesday report date.
    """
    w = daily.resample("W-FRI").last()
    p = pd.DataFrame(index=w.index)
    p["gold"] = w["gold"]
    p["r_gold"] = np.log(w["gold"]).diff()
    p["d_real"] = w["real"].diff()
    p["d_be"] = w["be"].diff()
    p["r_dxy"] = np.log(w["dxy"]).diff()
    p["d_vix"] = np.log(w["vix"]).diff()
    p["r_spx"] = np.log(w["spx"]).diff()
    p["r_oil"] = np.log(w["oil"].where(w["oil"] > 0)).diff()
    p["vix"] = w["vix"]
    if gld is not None:
        g = gld.sort_index()
        flow = (g["shares"].diff() * g["nav"]).resample("W-FRI").sum()
        aum = (g["shares"] * g["nav"]).resample("W-FRI").last().shift(1)
        p["flow"] = (flow / aum).reindex(p.index)
    if cot is not None:
        c = cot.sort_index()
        share = (c["mm_net"] / c["oi"]).resample("W-FRI").last()     # the week's Tuesday report
        p["mm_share"] = share.reindex(p.index)
        p["d_mm"] = p["mm_share"].diff()
    return p


# ------------------------------------------------------------------ attribution (descriptive)
def attribution(p: pd.DataFrame, factors: list[str] | None = None, window: int = ATTR_WINDOW) -> pd.DataFrame:
    """Each week's gold return split into factor contributions, using betas estimated on the previous
    `window` weeks only (so a week's split never uses that week's own data to fit the betas)."""
    factors = factors or [f for f in FACTORS if f in p]
    cols = ["r_gold"] + factors
    d = p[cols].dropna()
    rows = []
    for i in range(window, len(d)):
        past = d.iloc[i - window:i]
        X = np.column_stack([np.ones(window), past[factors].values])
        beta, *_ = np.linalg.lstsq(X, past["r_gold"].values, rcond=None)
        x = d.iloc[i]
        contrib = beta[1:] * x[factors].values
        rows.append({"week": d.index[i], "r_gold": x["r_gold"], "alpha": beta[0],
                     **{f"c_{f}": c for f, c in zip(factors, contrib)},
                     **{f"b_{f}": b for f, b in zip(factors, beta[1:])},
                     "residual": x["r_gold"] - beta[0] - contrib.sum()})
    return pd.DataFrame(rows).set_index("week")


def explained_share(attr: pd.DataFrame) -> float:
    """Out-of-sample R^2 of the attribution: share of weekly variance explained with past betas."""
    fitted = attr["r_gold"] - attr["residual"]
    return float(1 - ((attr["r_gold"] - fitted) ** 2).sum() / ((attr["r_gold"] - attr["r_gold"].mean()) ** 2).sum())


# ------------------------------------------------------------------ statistics helpers
def _hac(X: np.ndarray, y: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    xtx = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    s = u.T @ u
    for k in range(1, lags + 1):
        g = u[k:].T @ u[:-k]
        s += (1 - k / (lags + 1)) * (g + g.T)
    return beta, np.sqrt(np.diag(xtx @ s @ xtx))


def _nw_mean_se(f: np.ndarray, lags: int) -> float:
    f = f - f.mean()
    n = len(f)
    v = f @ f / n
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (f[k:] @ f[:-k]) / n
    return float(np.sqrt(max(v, 1e-300) / n))


# ------------------------------------------------------------------ H1 and H2
def decoupling(p: pd.DataFrame) -> dict:
    d = p[["r_gold", "d_real", "r_dxy"]].dropna()
    before = d.loc[DECOUPLE_BEFORE[0]:DECOUPLE_BEFORE[1]]
    after = d.loc[DECOUPLE_AFTER:]
    both = pd.concat([before, after])
    post = (both.index >= DECOUPLE_AFTER).astype(float)
    X = np.column_stack([np.ones(len(both)), post, both["d_real"], both["d_real"] * post])
    beta, se = _hac(X, both["r_gold"].values, 4)
    t = beta[3] / se[3]
    Xc = np.column_stack([X, both["r_dxy"], both["r_dxy"] * post])
    beta_c, se_c = _hac(Xc, both["r_gold"].values, 4)
    return {"beta_before": float(beta[2]), "beta_after": float(beta[2] + beta[3]), "diff": float(beta[3]),
            "t": float(t), "p_one_sided": float(stats.norm.sf(t)), "n_before": len(before), "n_after": len(after),
            "beta_before_ctrl": float(beta_c[2]), "beta_after_ctrl": float(beta_c[2] + beta_c[3]),
            "p_ctrl": float(stats.norm.sf(beta_c[3] / se_c[3])),
            "confirmed": bool(beta[3] > 0 and stats.norm.sf(t) < 0.05)}


def procyclical_flows(p: pd.DataFrame) -> dict:
    d = pd.DataFrame({"flow": p["flow"], "past4": p["r_gold"].rolling(4).sum().shift(1),
                      "same": p["r_gold"]}).dropna()
    X = np.column_stack([np.ones(len(d)), d["past4"]])
    beta, se = _hac(X, d["flow"].values, 4)
    t = beta[1] / se[1]
    return {"slope": float(beta[1]), "t": float(t), "p": float(2 * stats.norm.sf(abs(t))), "n": len(d),
            "first": str(d.index[0].date()), "corr_same_week": float(d["flow"].corr(d["same"])),
            "confirmed": bool(beta[1] > 0 and 2 * stats.norm.sf(abs(t)) < 0.05)}


# ------------------------------------------------------------------ H3 (out of sample)
def h3_panel(p: pd.DataFrame, h: int = H3_HORIZON) -> pd.DataFrame:
    """Signals known before each Friday origin: the CFTC report of the previous week (this week's comes out
    after the settlement) and GLD flows up to the previous week."""
    out = pd.DataFrame(index=p.index)
    out["target"] = np.log(p["gold"]).shift(-h) - np.log(p["gold"])
    out["mm_level"] = p["mm_share"].shift(1)
    out["mm_chg4"] = (p["mm_share"] - p["mm_share"].shift(4)).shift(1)
    out["flow4"] = p["flow"].rolling(4).sum().shift(1)
    return out


def oos(panel: pd.DataFrame, signal: str, h: int = H3_HORIZON, burn_in: int = H3_BURN_IN) -> pd.DataFrame:
    y, x = panel["target"].values, panel[signal].values
    rows = []
    for w in range(len(panel)):
        if np.isnan(x[w]):
            continue
        j = np.arange(0, w - h + 1)
        j = j[~np.isnan(x[j]) & ~np.isnan(y[j])]
        if len(j) < burn_in:
            continue
        b = np.cov(x[j], y[j], ddof=0)[0, 1] / np.var(x[j])
        a = y[j].mean() - b * x[j].mean()
        rows.append({"origin": panel.index[w], "outcome": y[w], "fc_model": a + b * x[w], "fc_mean": y[j].mean()})
    return pd.DataFrame(rows).set_index("origin")


def evaluate(fc: pd.DataFrame, h: int = H3_HORIZON) -> dict:
    r = fc.dropna(subset=["outcome"])
    em, eb = r.outcome - r.fc_model, r.outcome - r.fc_mean
    r2 = lambda a, b: float(1 - (a ** 2).sum() / (b ** 2).sum())  # noqa: E731
    f = (eb ** 2 - (em ** 2 - (r.fc_mean - r.fc_model) ** 2)).values
    t = float(f.mean() / _nw_mean_se(f, h - 1))
    half = len(r) // 2
    return {"n": len(r), "first": str(r.index[0].date()), "r2": r2(em, eb), "cw_p": float(stats.norm.sf(t)),
            "r2_early": r2(em[:half], eb[:half]), "r2_late": r2(em[half:], eb[half:])}


def h3(p: pd.DataFrame) -> pd.DataFrame:
    panel = h3_panel(p)
    rows = []
    for k, label in H3_CANDIDATES.items():
        res = evaluate(oos(panel, k))
        res["passes"] = bool(res["r2"] > 0 and res["cw_p"] < H3_P and res["r2_early"] > 0 and res["r2_late"] > 0)
        rows.append({"candidate": k, "label": label, **res})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ event study (descriptive)
def stress_selloffs(p: pd.DataFrame, vix_min: float = 30, drop: float = -0.04) -> pd.DataFrame:
    fwd = {h: np.log(p["gold"]).shift(-h) - np.log(p["gold"]) for h in (4, 13, 26)}
    ev = p[(p["vix"] >= vix_min) & (p["r_gold"] <= np.log(1 + drop))]
    rows = [{"week": d, "gold_week": float(np.expm1(p.loc[d, "r_gold"])), "vix": float(p.loc[d, "vix"]),
             **{f"fwd{h}": float(np.expm1(fwd[h].loc[d])) if pd.notna(fwd[h].loc[d]) else None for h in fwd}}
            for d in ev.index]
    return pd.DataFrame(rows)
