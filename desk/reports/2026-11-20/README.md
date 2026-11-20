# Gold report, 20 Nov 2026

Full report on gold's fall from the 2026 record, written at 13:45 ET on Friday 20 Nov (gold 3,506, -4.9% on the day, -9.8% on the week). It brings together the desk model and its track record, the macro backdrop, money flows and positioning, the comparison with past peaks since 1974, and every test run this month. Every key number is cross-checked against a second source or a recomputation; the 14 checks are listed at the end of the report and in `checks.json`.

- `gold_report_2026-11-20.pdf`: the report (8 pages)
- `results.json`: every number in the report; `checks.json`: the cross-checks with PASS/FAIL
- `data/`: snapshot used (Yahoo daily and 5-minute prices, FRED macro series, CFTC gold positioning, ICI money funds, State Street NAV and shares outstanding for GLD, SPY, XLK, XLU, XLP and BIL, monthly gold since 1833 from datahub), with `fetch_log.json` listing the last date of each source
- `scripts/`: `fetch_report.py <dir>/data` -> `analyse_report.py <dir>` -> `build_report.py <dir> <out.pdf>`, run from `desk/`

Prices are intraday, not settlements; today's close is scored in the weekly note. CFTC positioning is as of 10 Nov (the 17 Nov report was released at 15:30 ET, after this report). The breakeven tests are re-run here with the October 2025 CPI gap interpolated; the other test results are reloaded from the files where they were first committed.
