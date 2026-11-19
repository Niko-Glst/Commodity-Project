"""Gold cycles since 1975: peaks, falls, calm periods, and the rates/inflation backdrop of each.

Usage (from desk/): python reports/2026-11-19-cycles/scripts/analyse_cycles.py reports/2026-11-19-cycles
Monthly averages throughout (the only form that goes back to 1975); November 2026 is the average to date.
"""
import json
import sys

import numpy as np
import pandas as pd

N = sys.argv[1]
h = pd.read_csv(f"{N}/data/gold_monthly_datahub.csv")
h = pd.Series(h.Price.values, index=pd.PeriodIndex(h.Date, freq="M"))
gc = pd.read_csv(f"{N}/data/gc_daily.csv", index_col=0, parse_dates=True)["GC=F"]
f = pd.read_csv(f"{N}/data/fred_monthly.csv", index_col=0, parse_dates=True)
f.index = f.index.to_period("M")
tips = pd.read_csv(f"{N}/data/fred_dfii10_daily.csv", index_col=0, parse_dates=True).iloc[:, 0]
tips = tips.groupby(tips.index.to_period("M")).mean()

now_price, now_date = float(gc.iloc[-1]), gc.index[-1]
nov = gc.loc["2026-11"].mean()
m = pd.concat([h.loc["1970-01":"2026-10"], pd.Series([nov], index=pd.PeriodIndex(["2026-11"], freq="M"))])
# October 2025 CPI was never published (government shutdown): fill it by log-linear interpolation
cpi_all = np.exp(np.log(f["CPIAUCSL"]).interpolate(limit_area="inside"))
cpi = cpi_all.reindex(m.index).ffill()
real = m * cpi.iloc[-1] / cpi                                    # in October-2026 dollars
infl = cpi_all.pct_change(12, fill_method=None).mul(100).reindex(m.index).ffill()
rr = (f["GS10"].reindex(m.index).ffill() - infl)                 # ex-post real 10-year rate

# bear markets on monthly averages by the 20/20 rule, from 1974
s = m.loc["1974-01":]
peaks, bull, ext = [], True, 0
v = s.values
for i in range(1, len(v)):
    if bull:
        if v[i] > v[ext]:
            ext = i
        elif v[i] <= v[ext] * 0.8:
            pk, bull, ext = ext, False, i
    else:
        if v[i] < v[ext]:
            ext = i
        elif v[i] >= v[ext] * 1.2:
            peaks.append((pk, ext))
            bull, ext = True, i
if not bull:
    peaks.append((pk, ext))

rows = []
for pk, tr in peaks:
    p, t = s.index[pk], s.index[tr]
    after = s.iloc[pk + 1:]
    regain = after[after >= s.iloc[pk]]
    pre = s.iloc[max(0, pk - 48):pk + 1]
    low = pre.idxmin()
    real_after = real.loc[p:].iloc[1:]
    real_regain = real_after[real_after >= real.loc[p]]
    rows.append({
        "peak": str(p), "peak_avg": float(s.iloc[pk]), "real_peak": float(real.loc[p]),
        "runup_from": str(low), "runup_pct": float(s.iloc[pk] / pre.min() - 1), "runup_months": (p - low).n,
        "trough": str(t), "fall_pct": float(s.iloc[tr] / s.iloc[pk] - 1), "months_to_trough": (t - p).n,
        "regained": str(regain.index[0]) if len(regain) else None,
        "months_to_regain": (regain.index[0] - p).n if len(regain) else None,
        "real_regained": str(real_regain.index[0]) if len(real_regain) else None,
        "infl_at_peak": float(infl.loc[p]), "rr_at_peak": float(rr.loc[p]),
        "rr_change_peak_to_12m": float(rr.loc[min(p + 12, rr.index[-1])] - rr.loc[p]),
        "rr_runup_avg": float(rr.loc[low:p].mean()),
    })
peaks_df = pd.DataFrame(rows)

# post-peak paths and run-ups, monthly averages relative to the peak month
paths, runups = {}, {}
for r in rows:
    p = pd.Period(r["peak"], "M")
    after = m.loc[p:p + 72]
    paths[r["peak"]] = [float(x) for x in (after / after.iloc[0] - 1).values]
    before = m.loc[p - 60:p]
    runups[r["peak"]] = [float(x) for x in (before / before.iloc[-1]).values]

# calm periods, fixed by eye from the chart and described with the same statistics
CALM = [("1975-01", "1977-06", "After the 1974 peak"), ("1983-06", "2001-12", "The long quiet after 1980"),
        ("2013-07", "2019-05", "After the 2013 taper"), ("2020-09", "2023-10", "After the 2020 peak"),
        ("2026-02", "2026-11", "Now: since the 2026 peak")]
calm = []
for a, b, name in CALM:
    x = m.loc[a:b]
    ret = np.log(x).diff().dropna()
    yrs = len(x) / 12
    calm.append({"name": name, "from": a, "to": b, "years": yrs, "low": float(x.min()), "high": float(x.max()),
                 "range_pct": float(x.max() / x.min() - 1), "trend_pa": float((x.iloc[-1] / x.iloc[0]) ** (1 / max(yrs, 0.5)) - 1),
                 "vol": float(ret.std() * np.sqrt(12)), "infl": float(infl.loc[a:b].mean()), "rr": float(rr.loc[a:b].mean()),
                 "tips": float(tips.loc[a:b].mean()) if pd.Period(b, "M") >= pd.Period("2003-01", "M") else None,
                 "then_next5y": float(m.loc[pd.Period(b, "M"):pd.Period(b, "M") + 60].iloc[-1] / x.iloc[-1] - 1)
                 if pd.Period(b, "M") + 60 <= m.index[-1] else None})

major = [r["peak"] for r in rows]
gaps = [(pd.Period(major[i + 1], "M") - pd.Period(major[i], "M")).n / 12 for i in range(len(major) - 1)]
out = {
    "now_price": now_price, "now_date": str(now_date.date()), "nov_avg": float(nov), "cpi_month": str(f["CPIAUCSL"].dropna().index[-1]),
    "peaks": rows, "gaps_years": gaps, "paths": paths, "runups": runups, "calm": calm,
    "real_1980_peak_today": float(real.loc["1980-01"]), "real_2011_peak_today": float(real.loc["2011-09"]),
    "real_2026_peak": float(real.loc["2026-02"]), "now_real_rr": float(rr.iloc[-1]), "now_infl": float(infl.iloc[-1]),
    "now_tips": float(tips.iloc[-1]),
}
json.dump(out, open(f"{N}/cycles.json", "w"), indent=1)
pd.DataFrame({"gold_avg": m, "gold_real": real, "cpi_yoy": infl, "real_rate_expost": rr,
              "tips_10y": tips.reindex(m.index)}).to_csv(f"{N}/monthly.csv")
pd.set_option("display.width", 250)
print(peaks_df.round(3).to_string(index=False))
print(pd.DataFrame(calm).round(3).to_string(index=False))
print("gaps between peaks (years):", [round(g, 1) for g in gaps])
print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in out.items() if k not in ("peaks", "paths", "runups", "calm")})
for k, p in paths.items():
    print(k, "drawdown at months 3, 6, 9, 12, 24, 36:", [round(p[i], 2) if i < len(p) else None for i in (3, 6, 9, 12, 24, 36)])
