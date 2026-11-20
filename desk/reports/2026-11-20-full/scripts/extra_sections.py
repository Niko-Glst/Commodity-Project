# Appended to the 20 Nov analysis by make_analysis.py: where money is going, other markets after past gold peaks,
# sectors after past peaks. Runs after results.json and checks.json exist; adds results["extra"] and more checks.
res_ = json.load(open(N / "results.json"))
chk_ = json.load(open(N / "checks.json"))
etf = pd.read_csv(D / "etf_total_return.csv", index_col=0, parse_dates=True)
etf = etf[etf["SPY"].notna()]
NAMES = {"SPY": "S&P 500", "RSP": "S&P 500 equal weight", "QQQ": "Nasdaq-100", "IWM": "Small caps", "XLK": "Technology",
         "XLC": "Communication services", "XLY": "Consumer discretionary", "XLF": "Financials", "XLI": "Industrials",
         "XLE": "Energy", "XLB": "Materials", "XLV": "Health care", "XLP": "Consumer staples", "XLU": "Utilities",
         "XLRE": "Real estate", "SMH": "Semiconductors", "IGV": "Software", "BIL": "T-bills (cash)", "IEF": "Treasuries 7-10y",
         "TLT": "Treasuries 20y+", "UUP": "US dollar", "GLD": "Gold", "SLV": "Silver", "CPER": "Copper", "COPX": "Copper miners",
         "USO": "Oil", "EFA": "Developed markets", "EEM": "Emerging markets", "MTUM": "Momentum stocks", "USMV": "Low-volatility stocks"}


def tret(t, a, b=None):
    s = etf[t].dropna()
    s0 = s.loc[:a]
    if s0.empty:
        return None
    s1 = s.loc[:b] if b else s
    return float(s1.iloc[-1] / s0.iloc[-1] - 1)


last_etf = etf.index[-1]
perf_rows = []
for t, nm in NAMES.items():
    perf_rows.append({"ticker": t, "name": nm, "since_record": tret(t, "2026-01-29"), "since_oct6": tret(t, "2026-10-06"),
                      "week": tret(t, "2026-11-13"), "today": tret(t, f"{etf.index[-2]:%Y-%m-%d}")})
perf = pd.DataFrame(perf_rows).set_index("ticker")
GROUPS = [("AI and growth (semis, software, tech, Nasdaq-100)", ["SMH", "IGV", "XLK", "QQQ"]),
          ("Metals and miners (silver, copper, miners)", ["SLV", "CPER", "COPX"]),
          ("Gold", ["GLD"]),
          ("Defensive sectors (staples, health care, utilities)", ["XLP", "XLV", "XLU"]),
          ("Cyclical sectors (financials, industrials, energy, materials)", ["XLF", "XLI", "XLE", "XLB"]),
          ("Treasuries (7-10y, 20y+)", ["IEF", "TLT"]),
          ("US dollar", ["UUP"]), ("Cash (T-bills)", ["BIL"])]
groups = [{"group": g_, **{c: float(perf.loc[ts, c].mean()) for c in ("since_record", "since_oct6", "week", "today")}}
          for g_, ts in GROUPS]
mom_vs_lowvol = {c: float(perf.loc["MTUM", c] - perf.loc["USMV", c]) for c in ("since_record", "since_oct6", "week")}

# State Street flows for every SPDR
sflows = {}
for t in ["GLD", "SPY", "BIL", "XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE", "XSD", "XME"]:
    x = pd.read_excel(D / f"ssga_navhist_{t}.xlsx", header=None, engine="openpyxl")
    s0 = x.index[x[0].astype(str).str.strip() == "Date"][0] + 1
    x = x.iloc[s0:, :3]
    x.columns = ["date", "nav", "shares"]
    x["date"] = pd.to_datetime(x["date"], format="%d-%b-%Y", errors="coerce")
    x["nav"], x["shares"] = pd.to_numeric(x["nav"], errors="coerce"), pd.to_numeric(x["shares"], errors="coerce")
    x = x.dropna().sort_values("date").set_index("date")
    x["flow"], x["aum"] = x.shares.diff() * x.nav, x.shares * x.nav
    wk = x.flow.resample("W-FRI").sum()
    row = {"aum_bn": x.aum.iloc[-1] / 1e9, "last": str(x.index[-1].date())}
    for lab, st_ in (("since_record", "2026-01-29"), ("since_oct6", "2026-10-06"), ("week", "2026-11-13")):
        fl = x.loc[x.index > st_, "flow"].sum()
        row[f"{lab}_bn"], row[f"{lab}_pct"] = fl / 1e9, fl / x.loc[:st_, "aum"].iloc[-1]
    row["z_week"] = float((wk.iloc[-1] - wk.iloc[-53:-1].mean()) / wk.iloc[-53:-1].std())
    sflows[t] = row
    if t == "SPY":
        a0, a1 = x.loc[:"2026-10-06"].iloc[-1], x.iloc[-1]
        bridge = (a1.aum - a0.aum) - x.loc[x.index > "2026-10-06", "flow"].sum()
        perf_eff = (a1.nav / a0.nav - 1) * a0.aum
        chk_.append({"check": "SPY: asset bridge (change in assets = flows + price effect)",
                     "result": "PASS" if abs(bridge - perf_eff) / a0.aum < 0.02 else "FAIL",
                     "detail": f"price effect {perf_eff / 1e9:+.1f}bn vs assets minus flows {bridge / 1e9:+.1f}bn since 6 Oct"})

# stress gauges
sect = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE"]
sr = np.log(etf[sect].dropna()).diff().dropna()
iu = np.triu_indices(len(sect), 1)
corr21 = pd.Series({dt: sr.loc[:dt].tail(21).corr().values[iu].mean() for dt in sr.index[-400:]})
disp21 = sr.std(axis=1).rolling(21).mean().dropna()
mv = daily["^MOVE"].dropna()
stress = {"vix": cross["^VIX"]["now"], "vix_ratio": vix_ratio, "move": float(mv.iloc[-1]),
          "move_pct": float((mv.loc["2024":] < mv.iloc[-1]).mean()),
          "hy": float(fr["BAMLH0A0HYM2"].dropna().iloc[-1]),
          "hy_since_oct6_bp": 100 * float(fr["BAMLH0A0HYM2"].dropna().iloc[-1] - fr["BAMLH0A0HYM2"].dropna().loc[:"2026-10-06"].iloc[-1]),
          "corr21": float(corr21.iloc[-1]), "corr21_oct6": float(corr21.loc[:"2026-10-06"].iloc[-1]),
          "corr21_max": float(corr21.max()), "corr21_max_date": str(corr21.idxmax().date()),
          "disp_pct": float((disp21.loc["2024":] < disp21.iloc[-1]).mean())}

# other markets after past gold peaks (monthly averages; 9 months, as far as 2026 has run)
mon = lambda s: s.groupby(s.index.to_period("M")).mean()  # noqa: E731
spx_m = mon(daily["^GSPC"].dropna())
dxy_m = mon(daily["DX-Y.NYB"].dropna())
oil_m = fr["WTISPLC"].dropna()
oil_m.index = oil_m.index.to_period("M")
oil_m = pd.concat([oil_m, mon(daily["CL=F"].dropna()).loc[oil_m.index.max() + 1:]])
gs10 = fr["GS10"].dropna()
gs10.index = gs10.index.to_period("M")
gs10 = pd.concat([gs10, mon(fr["DGS10"].dropna()).loc[gs10.index.max() + 1:]])
ffr = fr["FEDFUNDS"].dropna()
ffr.index = ffr.index.to_period("M")
infl_m = (cpi.pct_change(12, fill_method=None) * 100)
infl_m.index = infl_m.index.to_period("M")
K = (m.index[-1] - pd.Period("2026-02", "M")).n
after = []
for pk_ in ("1974-12", "1980-01", "2008-03", "2011-09", "2026-02"):
    p = pd.Period(pk_, "M")
    q = min(p + K, m.index[-1])

    def at(s, t):
        s = s.dropna()
        return float(s.loc[:t].iloc[-1])

    after.append({"peak": pk_, "months": (q - p).n,
                  "gold": at(m, q) / at(m, p) - 1, "spx": at(spx_m, q) / at(spx_m, p) - 1,
                  "dollar": (at(dxy_m, q) / at(dxy_m, p) - 1) if p >= dxy_m.index.min() else None,
                  "oil": at(oil_m, q) / at(oil_m, p) - 1, "y10": at(gs10, q) - at(gs10, p),
                  "ffr": at(ffr, q) - at(ffr, p), "infl_then": at(infl_m, p), "infl_after": at(infl_m, q)})
gs_chk = pd.concat([gs10.loc["2001":"2026-10"], mon(daily["^TNX"].dropna()).loc["2001":"2026-10"]], axis=1).dropna()
chk_.append({"check": "10-year yield, monthly: FRED GS10 vs Yahoo ^TNX", "result":
             "PASS" if (gs_chk.iloc[:, 0] - gs_chk.iloc[:, 1]).abs().median() < 0.05 else "FAIL",
             "detail": f"{len(gs_chk)} months; median gap {(gs_chk.iloc[:, 0] - gs_chk.iloc[:, 1]).abs().median():.3f} pt"})
oil_chk = pd.concat([fr["WTISPLC"].dropna().rename(lambda d_: d_.to_period("M")).loc["2001":],
                     mon(daily["CL=F"].dropna()).loc["2001":]], axis=1).dropna()
dev = (oil_chk.iloc[:, 0] / oil_chk.iloc[:, 1] - 1).abs()
chk_.append({"check": "Oil, monthly: FRED WTI spot vs COMEX futures", "result": "PASS" if dev.median() < 0.02 else "FAIL",
             "detail": f"{len(oil_chk)} months; median gap {dev.median():.1%}"})
chk_.append({"check": "Long dollar series covers the 1974 and 1980 peaks", "result":
             "PASS" if dxy_m.index.min() <= pd.Period("1974-12", "M") else "FAIL",
             "detail": f"Yahoo dollar index monthly from {dxy_m.index.min()}"})

# sectors in the 9 months after the 2008 and 2011 gold peaks, and since the 2026 peak
SECT9 = ["XLK", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "SPY", "TLT", "GLD", "BIL"]
sect_after = {}
for pk_ in ("2008-03", "2011-09", "2026-02"):
    p = pd.Period(pk_, "M")
    a = f"{p.end_time:%Y-%m-%d}"
    b = f"{(p + K).end_time:%Y-%m-%d}" if pk_ != "2026-02" else None
    sect_after[pk_] = {t: tret(t, a, b) for t in SECT9}
rank = pd.DataFrame(sect_after).loc[["XLK", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU"]]
rank_corr = {pk_: float(stats.spearmanr(rank["2026-02"], rank[pk_])[0]) for pk_ in ("2008-03", "2011-09")}
bil_tr, bil_px = tret("BIL", "2026-01-29"), float(daily["GLD"].dropna().iloc[-1]) and None
chk_.append({"check": "Cash ETF earns its yield (total return positive since the record)",
             "result": "PASS" if perf.loc["BIL", "since_record"] > 0 else "FAIL",
             "detail": f"BIL total return since 29 Jan {perf.loc['BIL', 'since_record']:+.2%}"})

res_["extra"] = {"etf_last": str(last_etf.date()), "perf": json.loads(perf.reset_index().to_json(orient="records")),
                 "groups": groups, "mom_vs_lowvol": mom_vs_lowvol, "sflows": sflows, "stress": stress,
                 "after_peaks": after, "after_months": K, "sect_after": sect_after, "rank_corr": rank_corr}
(N / "results.json").write_text(json.dumps(res_, indent=1, default=float), encoding="utf-8")
(N / "checks.json").write_text(json.dumps(chk_, indent=1), encoding="utf-8")
print(pd.DataFrame(groups).round(3).to_string(index=False))
print(pd.DataFrame(after).round(3).to_string(index=False))
print(rank.round(3).to_string(), rank_corr)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in stress.items()})
print(pd.DataFrame(sflows).T[["since_record_bn", "since_oct6_bn", "week_bn", "z_week"]].astype(float).round(2).to_string())
for c in chk_[-6:]:
    print(f"[{c['result']}] {c['check']}: {c['detail']}")
