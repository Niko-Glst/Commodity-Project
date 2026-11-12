"""Today's gold move vs the GARCH-t model, plus volatility-clustering statistics."""
import sys, json
import numpy as np, pandas as pd
from scipy import stats
from arch import arch_model
N = sys.argv[1]
d = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
g = d["GC=F"].dropna()
TODAY = g.index[-1]; now = float(g.iloc[-1])
hist = g.iloc[:-1]                       # finished closes only (to yesterday)
y_close = float(hist.iloc[-1])
r = np.log(hist).diff().dropna()

def fit(series):
    rr = np.log(series).diff().dropna() * 100
    res = arch_model(rr, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
    var_next = float(res.forecast(horizon=1, reindex=False).variance.iloc[-1, 0]) / 1e4
    return res, var_next

res, var_next = fit(hist)
p = res.params; nu = float(p["nu"]); a, b = float(p["alpha[1]"]), float(p["beta[1]"])
om = float(p["omega"]) / 1e4; pers = a + b
sig = np.sqrt(var_next); scale = np.sqrt(nu / (nu - 2))
r_today = np.log(now / y_close); z_today = r_today / sig
p_today = stats.t.cdf(z_today * scale, nu)                     # standardised t
q = lambda pr: y_close * np.exp(stats.t.ppf(pr, nu) / scale * sig)
cond_sig = res.conditional_volatility / 100                     # sigma_t for each day
zs = (r - float(p["mu"]) / 100) / cond_sig.reindex(r.index)
vol_ann = cond_sig * np.sqrt(252)
lr_var = om / (1 - pers)
# vol term structure: average expected variance over the next h days
def avg_vol(h):
    v = [lr_var + pers ** k * (var_next - lr_var) for k in range(h)]
    return float(np.sqrt(np.mean(v) * 252))

# clustering: big day = |r| > 2 x full-sample sd; does a big day follow big days?
sd = r.std(); big = (r.abs() > 2 * sd)
prev5 = big.shift(1).rolling(5).max().fillna(0).astype(bool)
p_uncond = big.mean(); p_after = big[prev5].mean(); p_calm = big[~prev5].mean()
bigz = zs.abs() > 2 * zs.std()
prev5z = bigz.shift(1).rolling(5).max().fillna(0).astype(bool)
acf = lambda x, k: float(np.corrcoef(x[k:], x[:-k])[0, 1])
ra = r.abs().values; rv = r.values
recent = pd.DataFrame({"close": hist, "ret": np.expm1(r), "z": zs, "vol_ann": vol_ann}).loc["2026-10-15":]
big_recent = recent[recent["z"].abs() > 2]
pct_vol = float((vol_ann < np.sqrt(var_next * 252)).mean())

out = dict(
    today=str(TODAY.date()), now=now, y_close=y_close, y_date=str(hist.index[-1].date()),
    r_today=float(np.expm1(r_today)), z_today=float(z_today), pit_today=float(p_today),
    one_in=float(1 / p_today), band90=[q(0.05), q(0.95)], band98=[q(0.01), q(0.99)],
    sigma_day=float(sig), vol_next=float(sig * np.sqrt(252)), vol_lr=float(np.sqrt(lr_var * 252)),
    vol_pct_since_2003=pct_vol, alpha=a, beta=b, nu=nu, persistence=pers,
    half_life=float(np.log(.5) / np.log(pers)),
    term={h: avg_vol(h) for h in (5, 21, 63, 252)},
    clustering=dict(threshold_pct=float(2 * sd * 100), p_uncond=float(p_uncond), p_after_big=float(p_after),
                    p_after_calm=float(p_calm), ratio=float(p_after / p_calm),
                    z_p_after_big=float(bigz[prev5z].mean()), z_p_after_calm=float(bigz[~prev5z].mean()),
                    acf_abs=[acf(ra, k) for k in (1, 5, 21, 63)], acf_ret=[acf(rv, k) for k in (1, 5, 21, 63)]),
    big_days_since_oct15=[(str(i.date()), round(float(x.ret) * 100, 2), round(float(x.z), 2)) for i, x in big_recent.iterrows()],
    n_sessions_since_oct15=len(recent),
    peak=float(g.max()), peak_date=str(g.idxmax().date()), year_low_before=float(hist.loc["2026"].min()),
    year_low_date=str(hist.loc["2026"].idxmin().date()),
)
json.dump(out, open(f"{N}/today.json", "w"), indent=1, default=float)
recent.to_csv(f"{N}/recent.csv")
pd.DataFrame({"vol_model": vol_ann, "vol_real21": np.sqrt(252) * r.rolling(21).std()}).to_csv(f"{N}/vol_path.csv")
print(json.dumps(out, indent=1, default=float))
print(recent.tail(12).round(4).to_string())
