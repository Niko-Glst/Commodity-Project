"""This morning's gold move against the desk model, the 13 Nov forecast, and ranges from here.

Usage (from desk/): python reports/2026-11-18/scripts/analyse_today.py reports/2026-11-18
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))        # desk/ -> gold_desk
from gold_desk.backtest import iv_targets  # noqa: E402
from gold_desk.model import Fit, fit, simulate  # noqa: E402

N = sys.argv[1]
d = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(f"{N}/data/gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)
g = d["GC=F"].dropna()
TODAY, now = g.index[-1], float(intra["Close"].iloc[-1])
asof = intra.index[-1]
g.iloc[-1] = now                          # today's row = latest 5-minute print
hist = g.iloc[:-1]                        # finished closes, to Tuesday 17 Nov
y_close = float(hist.iloc[-1])
r = np.log(hist).diff().dropna()


def avg_vol(f: Fit, h: int) -> float:
    """Average expected annualised vol over the next h days."""
    lr = f.omega / (1 - f.persistence)
    v = [lr + f.persistence ** k * (f.var_next - lr) for k in range(h)]
    return float(np.sqrt(np.mean(v) * 252))


# ------------------------------------------------ today vs the model fitted to Tuesday's close
f0 = fit(hist)
sig, nu = np.sqrt(f0.var_next), f0.nu
sc = np.sqrt(nu / (nu - 2))
r_today = np.log(now / y_close)
z_today = r_today / sig
p_today = float(stats.t.cdf(z_today * sc, nu))
q = lambda pr: y_close * np.exp(stats.t.ppf(pr, nu) / sc * sig)  # noqa: E731

# conditional vol path (for the clustering chart): refit with arch to get sigma_t for each day
from arch import arch_model  # noqa: E402
res = arch_model(r * 100, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
cond = res.conditional_volatility / 100
zs = (r - float(res.params["mu"]) / 100) / cond
vol_ann = cond * np.sqrt(252)
pct_vol = float((vol_ann < f0.vol_next).mean())

# ------------------------------------------------ the 13 Nov weekly forecast, re-simulated exactly
live = [json.loads(x) for x in open(Path(__file__).resolve().parents[3] / "store" / "live.jsonl")]
rec = [x for x in live if x["origin"] == "2026-11-13"][0]
f13 = Fit(**rec["fit"])
k = len(g.loc["2026-11-14":])                                     # trading days since 13 Nov, today included
p13 = rec["spot"] * np.exp(simulate(f13, horizon=21)[:, 1:])      # same seed and fit: the paths of 13 Nov
pit13 = float((p13[:, k - 1] <= now).mean())
band13_k = [float(np.percentile(p13[:, k - 1], 5)), float(np.percentile(p13[:, k - 1], 95))]
band13_w = [float(np.percentile(p13[:, 4], 5)), float(np.percentile(p13[:, 4], 95))]
touch13 = float((p13.min(1) <= 3800).mean())
touch13_by_now = float((p13[:, :k].min(1) <= 3800).mean())        # chance it happened within k closes

# ------------------------------------------------ ranges from here (this morning's price as latest observation)
f1 = fit(g)
paths = now * np.exp(simulate(f1, horizon=21)[:, 1:])
fwd_dates = pd.bdate_range(TODAY + pd.Timedelta(days=1), periods=21)
fan = {p: np.percentile(paths, p, axis=0).tolist() for p in (5, 25, 50, 75, 95)}
LEVELS = (3600, 3700, 3900, 4000)
touch = {lvl: float((paths.min(1) <= lvl).mean() if lvl < now else (paths.max(1) >= lvl).mean()) for lvl in LEVELS}
touch_week = {lvl: float((paths[:, :5].min(1) <= lvl).mean() if lvl < now else (paths[:, :5].max(1) >= lvl).mean())
              for lvl in LEVELS}

# ------------------------------------------------ GVZ (options market), with the desk's bias correction
gvz = d["^GVZ"].dropna()
ivt = iv_targets(g, gvz).iloc[-1]
gvz_last_date = gvz.index[-1]
gvz_pct_1y = float((gvz.loc[gvz_last_date - pd.Timedelta(days=365):] < gvz.iloc[-1]).mean())

# ------------------------------------------------ clustering since 2003
sd = r.std()
big = r.abs() > 2 * sd
prev5 = big.shift(1).rolling(5).max().fillna(0).astype(bool)
bigz = zs.abs() > 2 * zs.std()
prev5z = bigz.shift(1).rolling(5).max().fillna(0).astype(bool)
acf = lambda x, k_: float(np.corrcoef(x[k_:], x[:-k_])[0, 1])  # noqa: E731
big2 = (r.loc["2026-10-15":].abs() > 0.02)

recent = pd.DataFrame({"close": hist, "ret": np.expm1(r), "z": zs, "vol_ann": vol_ann}).loc["2026-10-15":]
lower = g.loc[:"2026-11-17"]
low_since = lower[lower <= now].index.max()                        # last close at or below this morning's price

out = dict(
    today=str(TODAY.date()), asof=f"{asof:%H:%M}", now=now, y_close=y_close, y_date=str(hist.index[-1].date()),
    r_today=float(np.expm1(r_today)), z_today=float(z_today), pit_today=p_today, one_in=float(1 / p_today),
    band90=[q(0.05), q(0.95)], band98=[q(0.01), q(0.99)],
    session_low=float(intra.loc[f"{hist.index[-1]:%Y-%m-%d} 18:00":, "Low"].min()),
    session_low_t=f"{intra.loc[f'{hist.index[-1]:%Y-%m-%d} 18:00':, 'Low'].idxmin():%H:%M}",
    session_high=float(intra.loc[f"{hist.index[-1]:%Y-%m-%d} 18:00":, "High"].max()),
    sigma_day=float(sig), vol_next=f0.vol_next, vol_lr=f0.vol_long_run, vol_pct_since_2003=pct_vol,
    alpha=f0.alpha, beta=f0.beta, nu=nu, persistence=f0.persistence, half_life=f0.half_life,
    term={h: avg_vol(f0, h) for h in (5, 21, 63)},
    vol_next_now=f1.vol_next, term_now={h: avg_vol(f1, h) for h in (5, 21, 63)},
    f13=dict(spot=rec["spot"], k=k, pit=pit13, band_k=band13_k, band_week=band13_w,
             touch3800_month=touch13, touch3800_by_now=touch13_by_now, vol=f13.vol_next),
    fwd_dates=[f"{x:%Y-%m-%d}" for x in fwd_dates], fan=fan, touch=touch, touch_week=touch_week,
    gvz=dict(last=float(gvz.iloc[-1]), date=str(gvz_last_date.date()), pct_1y=gvz_pct_1y,
             correction=float(ivt["correction"]), corrected=float(ivt["iv_corrected"])),
    clustering=dict(threshold_pct=float(2 * sd * 100), p_after_big=float(big[prev5].mean()),
                    p_after_calm=float(big[~prev5].mean()), z_p_after_big=float(bigz[prev5z].mean()),
                    z_p_after_calm=float(bigz[~prev5z].mean()),
                    acf_abs=[acf(r.abs().values, k_) for k_ in (1, 5, 21)],
                    acf_ret=[acf(r.values, k_) for k_ in (1, 5, 21)]),
    moves_over_2pct_since_oct15=[(str(i.date()), round(float(np.expm1(x)) * 100, 2)) for i, x in r.loc["2026-10-15":][big2].items()],
    n_sessions_since_oct15=int(len(recent)),
    peak=float(g.max()), peak_date=str(g.idxmax().date()), ytd=float(now / g.loc[:"2025-12-31"].iloc[-1] - 1),
    low_since=str(low_since.date()), low_since_close=float(lower.loc[low_since]),
    year_low_before=float(hist.loc["2026"].min()), year_low_date=str(hist.loc["2026"].idxmin().date()),
    from_nov11=float(now / g.loc["2026-11-11"] - 1),
)
json.dump(out, open(f"{N}/today.json", "w"), indent=1, default=float)
recent.to_csv(f"{N}/recent.csv")
pd.DataFrame({"vol_model": vol_ann, "vol_real21": np.sqrt(252) * r.rolling(21).std()}).to_csv(f"{N}/vol_path.csv")
print(json.dumps({k_: v for k_, v in out.items() if k_ not in ("fan", "fwd_dates")}, indent=1, default=float))
