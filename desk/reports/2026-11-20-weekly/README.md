# Gold Desk Weekly Monitor, week to Friday 20 Nov 2026

A 14-slide landscape weekly. Its layout follows a weekly markets-monitor deck (highlights, chart of the week, cross-asset bars, all about gold, trading sessions, week ahead, performance table, driver attribution, last week's data, technicals, COMEX positioning in tonnes, ETF flows, volatility). Branding is the desk's own. All prices are Friday closes.

- `gold_weekly_monitor_2026-11-20.pdf`: the monitor
- `week.json`: every number in it; `drivers.json`: attribution and the pre-registered driver tests (H1-H3, rules in `gold_desk/drivers.py`, commit 0a7239c)
- `data/`: snapshot (Yahoo daily and 5-minute, FRED, CFTC disaggregated, State Street GLD/SPY/BIL, ICI, datahub monthly gold) with `fetch_log.json`; also used by `../2026-annual-review`
- `scripts/`: `fetch_week.py <dir>/data` -> `analyse_drivers.py <dir>` -> `build_weekly.py <dir>`, run from `desk/`

Notes: CSI 300 is left out (Yahoo has one data point). GLD tonnes = shares x ounces per share (60-day median of NAV / COMEX price). Week-ahead consensus comes from calendar providers via press; where they differ, a range is shown.
