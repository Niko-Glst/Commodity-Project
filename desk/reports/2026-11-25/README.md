# Nova Gold Weekly, edition 25 Nov 2026 (holiday week, to the Wednesday close)

Thanksgiving week: Thursday 26 Nov was a holiday and Friday 27 Nov a half day, so this note uses the Wednesday 25 Nov close, the last full session (after the October PCE, Q3 GDP and the Beige Book). It is a holiday-week note, not a weekly record: no forecast is logged, and the 27 Nov close is logged as the weekly record. The user asked for ETF and equity movement, the gold narratives (hawkish Fed and others) and gold's past cycles.

- `nova_gold_weekly_2026-11-25.pdf`: the Nova Gold Weekly (12 pages, the desk's teal slide style (structure from the internal Nova blueprint, which is not in the repo; previous look); internal: analysts and board). It replaces the 16-page `gold_desk_2026-11-25.pdf` (commit 415ee15); every change is in `CHANGELOG.md`
- `week.json`: every number in the note; `checks.json`: 17 data checks and 7 render checks, all PASS
- `data/`: snapshot (Yahoo daily prices to 26 Nov, cut at 25 Nov in the scripts; 5-minute GC=F and per-contract December/February bars; FRED; Treasury par real yield curve 2026; CFTC to 17 Nov; State Street NAV history for GLD, GLDM, SPY, XLK, XLU, XLP, BIL; ICI money funds to 24 Nov; datahub monthly gold), `fetch_log.json`
- `scripts/`: `fetch_week.py <dir>/data` -> `analyse_week.py` -> `build_note.py` (set `DESK_NOTE_OUT` to render elsewhere; uses `gold_desk/nova_style.py`, Windows fonts), run from `desk/`

Points to know:

- **Contracts:** GC=F is the December contract through 25 Nov (checked against GCZ26.CMX). From 26 Nov Yahoo's continuous series is the February contract, about $29 (0.8%) above December. The 27 Nov weekly change, and the scores of the 13 Nov 2-week and 30 Oct 1-month forecasts due on 30 Nov and 1 Dec, will contain that roll.
- **Monday's settlement** was $3,651.4. The 20 Nov note used a preliminary $3,632, so Monday's 1-day score moves from the 96.8th to the 98.0th percentile.
- **GLD check:** the first check, GLD's NAV against the COMEX settlement, failed at a weekly correlation of 0.922. The NAV is struck at the LBMA PM price (10:00 New York), and on volatile days that differs from the 13:30 settlement. The check now compares the daily NAV change with the 10:00 ET December bar for 23-25 Nov (within 0.5 pp) and GLD's market price with COMEX (weekly correlation 0.98). The threshold was not changed.
- **Wednesday:** December settled at $3,535.8 (13:30 ET) after a post-PCE low of $3,430 (10:15). It then rallied to $3,588 by 17:00. Press "closes" of $3,575-3,581 are later spot prices. GLD's NAV is struck at the LBMA PM price (10:00 New York), near the low, so it fell 4.3% on the day.
- **20 Nov forecast:** paths are rebuilt from the stored fit (seed 42, 20,000 paths; they reproduce the stored grids to within $0.01). Tuesday and Wednesday are shown as day-2 and day-3 percentiles for information; only the 1-day outcome is a score.
- **Shadow refit:** at Wednesday's close, through `model.fit`/`model.simulate`, not stored. `checks.json` records a sha256 of `store/live.jsonl` before and after.
- **Partial-week attribution:** uses betas from the 156 weeks to 20 Nov, without positioning (no CFTC report for 23-25 Nov) and without the intercept. The 25 Nov real yield comes from the Treasury par real curve, because FRED DFII10 ends on 24 Nov.
- **Cycles:** taken from `reports/2026-11-19-cycles/cycles.json`. All eight past peaks are used, and November 2026 is the COMEX average to 25 Nov (month to date).
- **Sources:** narratives cite dated sources. Single-source items are labelled: Nvidia news (BigGo Finance) and bank forecasts (Yahoo Finance, citing a Reuters poll).
