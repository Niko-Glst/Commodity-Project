# Gold full analysis, 20 Nov 2026

The 20 Nov report extended: gold's move (latest print 14:40 ET, 3,532), the macro backdrop, where money is going now (every sector and asset class against cash, State Street fund flows for 16 SPDR funds, stress gauges, and the macro mechanism checked against what happened), gold flows and positioning, the desk model, the past peaks, what other markets and sectors did after each gold peak, every test run this month, and 19 number checks (all PASS).

- `gold_full_analysis_2026-11-20.pdf`: the report (11 pages)
- `results.json` (every number), `checks.json` (cross-checks with PASS/FAIL)
- `data/`: snapshot used, with `fetch_log.json` listing the last date of each source
- `inputs/prior_tests.json`: the copper and rotation test results this report quotes, copied from `copper/` and `rotation/` on branch `copper-tech`, so the analysis also runs on `weekly-desk`
- `scripts/`:
  - `fetch_full.py <dir>/data`: downloads the snapshot
  - `make_analysis.py`: writes `analyse_full.py` from `../2026-11-20/scripts/analyse_report.py` plus `extra_sections.py`
  - `make_build.py`: writes `build_full.py` from `../2026-11-20/scripts/build_report.py` plus `part_*.py`
  - then `analyse_full.py <dir>` and `build_full.py <dir> <out.pdf>`, all run from `desk/`

Prices are intraday, not settlements. CFTC positioning is as of 10 Nov; the 17 Nov report came out at 15:30 ET, after this report.
