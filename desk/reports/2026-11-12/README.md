# Gold intraday note, 12 Nov 2026

One-off information note on the 12 Nov sell-off (gold −2.6% to $3,895 at 09:05 ET) and the current volatility cluster. It is separate from the weekly Friday-close note, and its prices are intraday, not a settlement.

- `gold_desk_intraday_2026-11-12.pdf`: the note (3 pages)
- `data/`: Yahoo Finance snapshot used (`daily.csv` since 2003, `gold_5m.csv` with 5-minute GC=F bars for 9–12 Nov)
- `today.json`, `recent.csv`: outputs of `analyse_today.py`
- `scripts/`: `fetch_today.py <dir>/data` → `analyse_today.py <dir>` → `build_today.py <dir> <out.pdf>`

Model: GARCH(1,1) with Student-t shocks and zero drift, fitted on finished closes up to 11 Nov; 20,000 Monte Carlo paths, seed 42. To rebuild from the saved snapshot, skip `fetch_today.py` and run the other two scripts with this folder as `<dir>`.
