"""Gold's bull and bear cycles on monthly averages (added 27 Nov 2026 for the Nova Gold Weekly).

Definitions, fixed here so every edition uses the same ones:
- Bear market (20/20 rule): from a peak, a fall of 20% or more in the monthly average, ended by a rise of 20% or
  more from the low. `bear_markets` returns (peak, trough) pairs.
- Rise before a peak: trough to peak, from the trough of the preceding bear market under the same rule. For the
  first peak there is no preceding bear market in the window; its rise is measured from the lowest monthly average
  since `base_start` (the end of the fixed gold price; the default is 1970-01).
- Real rate: the 10-year Treasury yield minus CPI inflation over the past 12 months ("nominal minus trailing
  inflation"), for every cycle. It is a backward-looking proxy, not a true ex-post real rate, which would use the
  inflation realised over the following ten years. The 10-year TIPS yield (monthly mean of DFII10) is a separate
  column from 2003, when it starts. Monthly averages understate the daily peaks and troughs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def bear_markets(s: pd.Series, threshold: float = 0.2) -> list[tuple]:
    """(peak, trough) index labels of each bear market in `s` (monthly averages)."""
    v = s.values
    out, bull, ext, pk = [], True, 0, None
    for i in range(1, len(v)):
        if bull:
            if v[i] > v[ext]:
                ext = i
            elif v[i] <= v[ext] * (1 - threshold):
                pk, bull, ext = ext, False, i
        else:
            if v[i] < v[ext]:
                ext = i
            elif v[i] >= v[ext] * (1 + threshold):
                out.append((s.index[pk], s.index[ext]))
                bull, ext = True, i
    if not bull:
        out.append((s.index[pk], s.index[ext]))
    return out


def rise_before(s_full: pd.Series, bears: list[tuple], base_start) -> list[dict]:
    """Trough-to-peak rise before each peak: from the preceding bear market's trough (first peak: the low since
    `base_start`)."""
    rows = []
    for k, (pk, _tr) in enumerate(bears):
        start = bears[k - 1][1] if k > 0 else s_full.loc[base_start:pk].idxmin()
        rows.append({"peak": pk, "from": start, "rise": float(s_full.loc[pk] / s_full.loc[start] - 1),
                     "months": int((pk - start).n) if hasattr(pk - start, "n") else None})
    return rows


def trailing_real_rate(gs10: pd.Series, cpi: pd.Series) -> pd.Series:
    """10-year yield minus CPI inflation over 12 months, monthly. Missing CPI months inside the series (October
    2025) are filled by log-linear interpolation so a 12-month change never silently becomes 13 months."""
    cpi = np.exp(np.log(cpi.astype(float)).interpolate(limit_area="inside"))
    infl = cpi.pct_change(12, fill_method=None) * 100
    return (gs10.astype(float) - infl).dropna()


def tips_monthly(dfii10_daily: pd.Series) -> pd.Series:
    """Monthly mean of the daily 10-year TIPS yield, indexed by month period."""
    s = dfii10_daily.dropna()
    return s.groupby(s.index.to_period("M")).mean()
