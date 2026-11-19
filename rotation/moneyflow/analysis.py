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


EQUITY_SECTORS = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE", "SMH", "IGV"]


def _ols_t(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and HC1 robust t-values (X includes the constant)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n, k = X.shape
    xtx = np.linalg.inv(X.T @ X)
    cov = xtx @ (X.T * e ** 2) @ X @ xtx * n / (n - k)
    return beta, beta / np.sqrt(np.diag(cov))


def robustness(p: pd.DataFrame, starts=("2026-10-01", "2026-10-06", "2026-10-15", "2026-11-01")) -> pd.DataFrame:
    """Post-hoc checks of the profit-taking test (added 19 Nov after review, not part of the original test).

    For each start date s: momentum = return over the 12 months to s, reaction = return since s.
    - raw: Spearman of momentum and reaction (s = 6 Oct is the original test)
    - vol-scaled: both divided by the asset's own volatility over the 12 months (risk-adjusted)
    - controls: OLS of reaction on momentum plus volatility, and on momentum plus beta to SPY;
      the t-value on momentum says whether winners fell more than their risk alone explains
    - equities only: the 11 sectors plus semiconductors and software
    """
    rows = []
    r = np.log(p).diff()
    for s in starts:
        s0 = f"{pd.Timestamp(s) - pd.DateOffset(years=1):%Y-%m-%d}"
        mom, react = ret(p, s0, s), ret(p, s)
        win = r.loc[s0:s]
        vol = win.std() * np.sqrt(252)
        beta = win.cov()["SPY"] / win["SPY"].var()
        days = len(p.loc[s:]) - 1
        for universe, cols in (("All 28", [c for c in p.columns if c != CASH]), ("Equity sectors", EQUITY_SECTORS)):
            m, y, v, bt = mom[cols], react[cols], vol[cols], beta[cols]
            raw = stats.spearmanr(m, y)
            scaled = stats.spearmanr(m / v, y / (v * np.sqrt(days / 252)))
            one = np.ones(len(cols))
            _, t_vol = _ols_t(y.values, np.column_stack([one, m.values, v.values]))
            _, t_beta = _ols_t(y.values, np.column_stack([one, m.values, bt.values]))
            rows.append({"start": s, "universe": universe, "n": len(cols), "raw": raw[0], "raw_p": raw[1],
                         "scaled": scaled[0], "scaled_p": scaled[1], "t_mom_vol": t_vol[1], "t_mom_beta": t_beta[1]})
    return pd.DataFrame(rows)


def _level_rows(F: dict, ids: dict, since: str = PEAK) -> list[dict]:
    rows = []
    for sid, label in ids.items():
        s = F[sid].dropna()
        d5 = s.diff(5).dropna()
        sd = d5.loc[s.index[-1] - pd.Timedelta(days=365):].std()
        rows.append({"series": label, "id": sid, "date": s.index[-1], "now": s.iloc[-1],
                     "at_peak": s.loc[:since].iloc[-1], "chg_peak_bp": 100 * (s.iloc[-1] - s.loc[:since].iloc[-1]),
                     "chg_1w_bp": 100 * (s.iloc[-1] - s.iloc[-6]), "z_1w": (s.iloc[-1] - s.iloc[-6]) / sd,
                     "pct_since_2024": float((s.loc["2024":] < s.iloc[-1]).mean()),
                     "max_since_2024": s.loc["2024":].max(), "max_date": s.loc["2024":].idxmax()})
    return rows


def credit_and_rates(F: dict) -> pd.DataFrame:
    """Credit spreads (widening = real risk-off) and the rate move, split into real yield and inflation."""
    return pd.DataFrame(_level_rows(F, {
        "BAMLH0A0HYM2": "High-yield spread", "BAMLC0A0CM": "Investment-grade spread",
        "DGS2": "2-year yield", "DGS10": "10-year yield", "DFII10": "10-year real yield",
        "T10YIE": "10-year breakeven inflation"}))


def stress(m: pd.DataFrame, p: pd.DataFrame) -> dict:
    """Equity and bond volatility, the VIX curve, and how tightly sectors move together."""
    ratio = m["^VIX"] / m["^VIX3M"]
    sect = EQUITY_SECTORS[:11]
    r = np.log(p[sect]).diff().dropna()
    iu = np.triu_indices(len(sect), 1)
    corr = pd.Series({d: r.loc[:d].tail(21).corr().values[iu].mean() for d in r.index[250:]})
    disp = r.std(axis=1).rolling(21).mean().dropna()
    inverted = ratio[ratio > 1]
    return {
        "vix": m["^VIX"].iloc[-1], "vix9d": m["^VIX9D"].iloc[-1], "vix3m": m["^VIX3M"].iloc[-1],
        "ratio": ratio.iloc[-1], "ratio_peak": ratio.loc[:PEAK].iloc[-1],
        "inverted_days_recent": [f"{d:%d %b}" for d in inverted.loc["2026-11-01":].index],
        "inverted_share_since_2024": float((ratio.loc["2024":] > 1).mean()),
        "ratio_max": ratio.loc["2024":].max(), "ratio_max_date": ratio.loc["2024":].idxmax(),
        "move": m["^MOVE"].iloc[-1], "move_peak": m["^MOVE"].loc[:PEAK].iloc[-1],
        "move_pct": float((m["^MOVE"].loc["2024":] < m["^MOVE"].iloc[-1]).mean()),
        "corr": corr.iloc[-1], "corr_peak": corr.loc[:PEAK].iloc[-1], "corr_pct": float((corr < corr.iloc[-1]).mean()),
        "corr_max": corr.max(), "corr_max_date": corr.idxmax(),
        "disp_pct": float((disp.loc["2024":] < disp.iloc[-1]).mean()),
    }


def factors(m: pd.DataFrame) -> dict:
    """Momentum unwind (MTUM vs SPY and min-vol) and whether XLY's gain is broad (vs equal weight)."""
    since = ret(m, PEAK)
    week = ret(m, f"{m.index[-1] - pd.Timedelta(days=7):%Y-%m-%d}")
    return {"mtum_vs_spy": since["MTUM"] - since["SPY"], "mtum_vs_usmv": since["MTUM"] - since["USMV"],
            "mtum_vs_spy_week": week["MTUM"] - week["SPY"],
            "xly": since["XLY"], "rspd": since["RSPD"],
            "names": {t: since[t] for t in ("AMZN", "TSLA", "HD", "MCD")}}


def etf_flows(flows: pd.DataFrame) -> pd.DataFrame:
    """Daily creations and redemptions from shares outstanding: flow = change in shares x NAV."""
    from .data import SSGA_NAMES

    f = flows.sort_values(["ticker", "date"]).copy()
    f["flow"] = f.groupby("ticker").shares.diff() * f.nav
    f["aum"] = f.shares * f.nav
    last = f.date.max()
    week_start = last - pd.Timedelta(days=7)
    weekly = f.set_index("date").groupby("ticker").flow.resample("W-WED").sum().unstack(0)
    rows = []
    for t, g in f.groupby("ticker"):
        row = {"ticker": t, "name": SSGA_NAMES[t], "aum_bn": g.aum.iloc[-1] / 1e9}
        for label, start in (("peak", PEAK), ("nov", "2026-10-30"), ("week", f"{week_start:%Y-%m-%d}")):
            flow = g.loc[g.date > start, "flow"].sum()
            row[f"flow_{label}_bn"] = flow / 1e9
            row[f"flow_{label}_pct"] = flow / g.loc[g.date <= start, "aum"].iloc[-1]
        w = weekly[t].dropna()
        row["z_week"] = (w.iloc[-1] - w.iloc[-53:-1].mean()) / w.iloc[-53:-1].std()
        rows.append(row)
    return pd.DataFrame(rows)


def mmf_stats(mmf: pd.DataFrame) -> dict:
    chg = mmf.total.diff().dropna()
    prior = chg.iloc[:-1]
    return {"date": mmf.index[-1], "total_tn": mmf.total.iloc[-1] / 1e6, "chg_bn": chg.iloc[-1] / 1e3,
            "z": (chg.iloc[-1] - prior.mean()) / prior.std(), "n_weeks": len(prior),
            "prev_date": mmf.index[-2], "prev_total_tn": mmf.total.iloc[-2] / 1e6, "prev_chg_bn": chg.iloc[-2] / 1e3,
            "prev_z": (chg.iloc[-2] - chg.iloc[:-2].mean()) / chg.iloc[:-2].std(),
            "first": mmf.index[0], "sd_bn": prior.std() / 1e3}


def net_liquidity(F: dict) -> dict:
    """Fed balance sheet minus the Treasury's cash account minus reverse repo, $bn (weekly).
    Reserves (WRESBAL) are already net of the TGA and reverse repo, so they are not combined with them."""
    walcl, tga = F["WALCL"].dropna(), F["WTREGEN"].dropna()
    rrp = F["RRPONTSYD"].dropna().reindex(walcl.index, method="ffill")
    nl = ((walcl - tga.reindex(walcl.index)) / 1e3 - rrp).dropna()
    return {"date": nl.index[-1], "now_bn": nl.iloc[-1], "at_peak_bn": nl.loc[:PEAK].iloc[-1],
            "chg_4w_bn": nl.iloc[-1] - nl.iloc[-5]}


def groups_by_start(p: pd.DataFrame, starts=("2026-10-01", "2026-10-06", "2026-10-15", "2026-11-01")) -> pd.DataFrame:
    rows = []
    for name, ts in GROUPS:
        row = {"group": name}
        for s in starts:
            row[s] = float(ret(p[ts], s).mean())
        rows.append(row)
    return pd.DataFrame(rows)


GROUPS = [("AI and growth (semis, tech, software, Nasdaq-100)", ["SMH", "XLK", "IGV", "QQQ"]),
          ("Silver, copper, copper miners", ["SLV", "CPER", "COPX"]),
          ("Gold", ["GLD"]),
          ("Defensive sectors (staples, health care, utilities, real estate)", ["XLP", "XLV", "XLU", "XLRE"]),
          ("Cyclical sectors (financials, discretionary, industrials)", ["XLF", "XLY", "XLI"]),
          ("Long Treasuries and the dollar", ["TLT", "UUP"]),
          ("T-bills (cash)", [CASH])]


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
