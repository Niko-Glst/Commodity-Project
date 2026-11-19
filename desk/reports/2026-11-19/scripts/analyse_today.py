"""19 Nov summary note: today's move against the desk model, the earlier forecasts, the drivers in numbers.

Usage (from desk/): python reports/2026-11-19/scripts/analyse_today.py reports/2026-11-19
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DESK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DESK))
from gold_desk.backtest import iv_targets  # noqa: E402
from gold_desk.model import Fit, fit, simulate  # noqa: E402

N = sys.argv[1]
d = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(f"{N}/data/gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)
fred = pd.read_csv(f"{N}/data/fred.csv", index_col=0, parse_dates=True)
cftc = pd.read_csv(f"{N}/data/cftc_gold.csv")
g = d["GC=F"].dropna()
TODAY, now, asof = g.index[-1], float(intra["Close"].iloc[-1]), intra.index[-1]
g.iloc[-1] = now
hist = g.iloc[:-1]
y_close = float(hist.iloc[-1])
session = intra.loc[f"{hist.index[-1]:%Y-%m-%d} 18:00":]


def avg_vol(f: Fit, h: int) -> float:
    lr = f.omega / (1 - f.persistence)
    return float(np.sqrt(np.mean([lr + f.persistence ** k * (f.var_next - lr) for k in range(h)]) * 252))


# today against the model fitted to yesterday's close
f0 = fit(hist)
sig, nu = np.sqrt(f0.var_next), f0.nu
sc = np.sqrt(nu / (nu - 2))
z_today = np.log(now / y_close) / sig
p_today = float(stats.t.cdf(z_today * sc, nu))
q = lambda pr: y_close * np.exp(stats.t.ppf(pr, nu) / sc * sig)  # noqa: E731

# earlier forecasts: the 13 Nov weekly (stored fit, same seed) and the 18 Nov flash note
live = [json.loads(x) for x in open(DESK / "store" / "live.jsonl")]
rec = [x for x in live if x["origin"] == "2026-11-13"][0]
f13 = Fit(**rec["fit"])
k = len(g.loc["2026-11-14":])
p13 = rec["spot"] * np.exp(simulate(f13, horizon=21)[:, 1:])
flash = json.load(open(DESK / "reports" / "2026-11-18" / "today.json"))

# ranges from here, this morning's price as the latest observation
f1 = fit(g)
paths = now * np.exp(simulate(f1, horizon=21)[:, 1:])
LEVELS = (3500, 3600, 3800, 4000)
touch = {lvl: float((paths.min(1) <= lvl).mean() if lvl < now else (paths.max(1) >= lvl).mean()) for lvl in LEVELS}
touch_w = {lvl: float((paths[:, :5].min(1) <= lvl).mean() if lvl < now else (paths[:, :5].max(1) >= lvl).mean())
           for lvl in LEVELS}
fan = {p: np.percentile(paths, p, axis=0).tolist() for p in (5, 25, 50, 75, 95)}
r = np.log(hist).diff().dropna()
vol_path = []
from arch import arch_model  # noqa: E402
res = arch_model(r * 100, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
cond = res.conditional_volatility / 100 * np.sqrt(252)
pct_vol = float((cond < f1.vol_next).mean())

# GVZ with the desk's premium correction
ivt = iv_targets(g, d["^GVZ"].dropna()).iloc[-1]

# drivers
real, be, two, hy = (fred[c].dropna() for c in ("DFII10", "T10YIE", "DGS2", "BAMLH0A0HYM2"))
pre26 = real.loc[:"2025-12-31"]
real_last_higher_pre2026 = pre26[pre26 >= real.iloc[-1]].index.max()
dxy = d["DX-Y.NYB"].dropna()
c = cftc.astype({"m_money_positions_long_all": float, "m_money_positions_short_all": float, "open_interest_all": float})
net = c.m_money_positions_long_all - c.m_money_positions_short_all


def chg(t, start):
    s = d[t].dropna()
    s = s.copy()
    if t == "GC=F":
        s.iloc[-1] = now
    a = s.loc[:start].iloc[-1]
    return float(s.iloc[-1] - a) if t in ("^TNX", "^VIX", "^GVZ") else float(s.iloc[-1] / a - 1)


cross = {t: {"now": float(now if t == "GC=F" else d[t].dropna().iloc[-1]), "since_peak": chg(t, "2026-10-06"),
             "since_13nov": chg(t, "2026-11-13"), "today": chg(t, f"{hist.index[-1]:%Y-%m-%d}")}
         for t in ("GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^TNX", "^GSPC", "^VIX", "^GVZ", "BTC-USD")}
low_since = hist[hist <= now].index.max()

out = dict(
    today=str(TODAY.date()), asof=f"{asof:%H:%M}", now=now, y_close=y_close, y_date=str(hist.index[-1].date()),
    r_today=now / y_close - 1, z_today=float(z_today), pit_today=p_today, band90=[q(0.05), q(0.95)],
    session_low=float(session["Low"].min()), session_low_t=f"{session['Low'].idxmin():%H:%M}",
    session_high=float(session["High"].max()),
    two_day=now / float(hist.loc[:"2026-11-17"].iloc[-1]) - 1, week=now / float(hist.loc[:"2026-11-13"].iloc[-1]) - 1,
    from_oct30=now / float(hist.loc[:"2026-10-30"].iloc[-1]) - 1,
    peak=float(g.max()), peak_date=str(g.idxmax().date()), low_since=str(low_since.date()),
    vol_prev=f0.vol_next, vol_now=f1.vol_next, vol_pct=pct_vol, vol_lr=f1.vol_long_run,
    term={h: avg_vol(f1, h) for h in (5, 21)},
    f13=dict(k=k, pit=float((p13[:, k - 1] <= now).mean()), band_k=[float(np.percentile(p13[:, k - 1], 5)),
             float(np.percentile(p13[:, k - 1], 95))], band_week=[float(np.percentile(p13[:, 4], 5)),
             float(np.percentile(p13[:, 4], 95))]),
    flash=dict(now=flash["now"], touch3700_week=flash["touch_week"]["3700"], touch3600_week=flash["touch_week"]["3600"]),
    fan=fan, touch=touch, touch_week=touch_w,
    gvz=dict(last=float(d["^GVZ"].dropna().iloc[-1]), date=str(d["^GVZ"].dropna().index[-1].date()),
             corrected=float(ivt["iv_corrected"])),
    real=dict(now=float(real.iloc[-1]), date=str(real.index[-1].date()), wk_bp=100 * float(real.iloc[-1] - real.iloc[-6]),
              peak_bp=100 * float(real.iloc[-1] - real.loc[:"2026-10-06"].iloc[-1]),
              max26=float(real.loc["2026"].max()), max26_date=str(real.loc["2026"].idxmax().date()),
              last_higher_pre2026=str(real_last_higher_pre2026.date()) if pd.notna(real_last_higher_pre2026) else None),
    breakeven=dict(now=float(be.iloc[-1]), date=str(be.index[-1].date()),
                   peak_bp=100 * float(be.iloc[-1] - be.loc[:"2026-10-06"].iloc[-1])),
    two_year=dict(now=float(two.iloc[-1]), wk_bp=100 * float(two.iloc[-1] - two.iloc[-6])),
    hy=dict(now=float(hy.iloc[-1]), date=str(hy.index[-1].date()), peak_bp=100 * float(hy.iloc[-1] - hy.loc[:"2026-10-06"].iloc[-1])),
    dxy=dict(now=float(dxy.iloc[-1]), last_higher=str(dxy.iloc[:-2][dxy.iloc[:-2] >= dxy.iloc[-1]].index.max().date())),
    cftc=dict(date=str(c.report_date_as_yyyy_mm_dd.iloc[-1])[:10], net=float(net.iloc[-1]), chg=float(net.iloc[-1] - net.iloc[-2]),
              pct_oi=float(net.iloc[-1] / c.open_interest_all.iloc[-1]),
              range=float((net.iloc[-1] - net.min()) / (net.max() - net.min()))),
    cross=cross,
)
json.dump(out, open(f"{N}/today.json", "w"), indent=1, default=float)
print(json.dumps({k_: v for k_, v in out.items() if k_ != "fan"}, indent=1, default=float))
