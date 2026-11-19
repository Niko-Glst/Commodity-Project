# Gold summary note, 19 Nov 2026

One-off note on why gold is falling: gold at $3,690 at 12:30 ET (-1.4% today, -4.5% in two days, -31% from the January record), the lowest since September 2025. It pulls together the desk model, the 13 Nov and 18 Nov forecasts, the Fed minutes of 18 Nov and the cross-asset work of the rotation side project. Prices are intraday, not a settlement. No forecast was added to the live log.

- `gold_desk_summary_2026-11-19.pdf`: the note (3 pages)
- `data/`: snapshot used (`daily.csv` from Yahoo since 2003, `gold_5m.csv` with 5-minute GC=F bars for 13-19 Nov, `fred.csv` with real yield, breakeven, 2- and 10-year yields and the high-yield spread, `cftc_gold.csv` with managed-money positions)
- `today.json`: output of `analyse_today.py`
- `scripts/`: `fetch_today.py <dir>/data` -> `analyse_today.py <dir>` -> `build_today.py <dir> <out.pdf>`, run from `desk/`

Model: the desk's GARCH(1,1) with Student-t shocks and zero drift, 20,000 paths, seed 42. Today's move is scored against the fit to the 18 Nov close; the 13 Nov comparison re-simulates that week's stored live fit. To rebuild from the saved snapshot, skip `fetch_today.py`.
