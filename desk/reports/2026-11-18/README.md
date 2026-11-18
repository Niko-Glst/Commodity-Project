# Gold flash note, 18 Nov 2026

One-off information note on the overnight break below $3,800 (gold −2.4% to $3,771 at 03:25 ET, the lowest since 24 Sep 2025), scored against the weekly forecast of 13 Nov. It is separate from the weekly Friday-close note, and its prices are intraday, not a settlement. No forecast was added to the live log.

- `gold_desk_flash_2026-11-18.pdf`: the note (3 pages)
- `data/`: Yahoo Finance snapshot used (`daily.csv` since 2003, including the GVZ and S&P 500 futures; `gold_5m.csv` with 5-minute GC=F bars for 12–18 Nov)
- `today.json`, `recent.csv`: outputs of `analyse_today.py`
- `scripts/`: `fetch_today.py <dir>/data` → `analyse_today.py <dir>` → `build_today.py <dir> <out.pdf>`, run from `desk/`

Model: the desk's GARCH(1,1) with Student-t shocks and zero drift (`gold_desk.model`), 20,000 paths, seed 42. Today's move is scored against the fit on finished closes up to 17 Nov. The 13 Nov comparison re-simulates the stored fit of that live record, which reproduces its paths exactly. To rebuild from the saved snapshot, skip `fetch_today.py` and run the other two scripts with this folder as `<dir>`.
