# Gold report, 20 Nov 2026

Full report on gold's fall from the 2026 record, written at 13:45 ET on Friday 20 Nov (gold 3,506, -4.9% on the day, -9.8% on the week). It brings together the desk model and its track record, the macro backdrop, money flows and positioning, the comparison with past peaks since 1974, and every test run this month. Every key number is cross-checked against a second source or a recomputation; the 14 checks are listed at the end of the report and in `checks.json`.

- `gold_report_2026-11-20.pdf`: the report (8 pages)
- `results.json`: every number in the report; `checks.json`: the cross-checks with PASS/FAIL
- `data/`: snapshot used (Yahoo daily and 5-minute prices, FRED macro series, CFTC gold positioning, ICI money funds, State Street NAV and shares outstanding for GLD, SPY, XLK, XLU, XLP and BIL, monthly gold since 1833 from datahub), with `fetch_log.json` listing the last date of each source
- `scripts/`: `fetch_report.py <dir>/data` -> `analyse_report.py <dir>` -> `build_report.py <dir> <out.pdf>`, run from `desk/`

Prices are intraday, not settlements; today's close is scored in the weekly note. CFTC positioning is as of 10 Nov (the 17 Nov report was released at 15:30 ET, after this report). The breakeven tests are re-run here with the October 2025 CPI gap interpolated; the other test results are reloaded from the files where they were first committed.

## Weekly desk note (added 23 Nov 2026)

The regular weekly note on Friday's close, with the weekend and the Sunday open to 22 Nov 23:55 ET, built in the landscape weekly-monitor layout of `reference/` (own branding). It reuses the Friday data and driver results of `reports/2026-11-20-weekly/` and adds the live forecast, the scorecard and the weekend.

- `gold_desk_2026-11-20.pdf`: the note (22 slides; Monday 23 Nov and the spring test added on 23 Nov evening)
- `summary.json`: written by `python -m gold_desk forecast --asof 2026-11-20` (live record 3 in `store/live.jsonl`)
- `desk_week.json`: every number in the note, including the scorecard, touch probabilities and weekend moves
- `data/weekend_5m.csv`: Yahoo 5-minute futures (GC=F, SI=F, ES=F, DX-Y.NYB, BTC-USD, ZN=F) from 20 to 23 Nov; 5-minute bars can only be fetched for about 60 days
- `scripts/build_desk_weekly.py`: renders the note, run from `desk/` (set `DESK_NOTE_OUT` to render elsewhere)
- `spring.json`: the pre-registered spring tests H4-H6 (rules in `gold_desk/spring.py`, commit 59b21e2, run after it), the 3-sigma event study, the Kalman fit, Monday's close in Friday's forecast and Monday through the driver betas; `scripts/analyse_spring.py` writes it
- `data/spring_panel.csv` (stretch and forward moves per weekly origin), `data/spring_state.csv` (Kalman value and stretch), `data/monday_daily.csv` and `data/monday_5m.csv` (Yahoo, Monday closes preliminary)

Forecast dates count COMEX trading days and treat Thanksgiving (26 Nov) as a holiday, so "1 week" ends Mon 30 Nov. `summary.json` itself still counts plain business days (27 Nov). News items are from CNBC, Fortune and FinanceFeeds; the Kitco survey and analyst levels are second-hand via FinanceFeeds and labelled as such.
