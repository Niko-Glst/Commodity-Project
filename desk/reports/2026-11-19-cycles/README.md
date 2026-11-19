# Gold cycles since 1975, 19 Nov 2026

One-off note asked for on 19 Nov: do gold's peaks and quiet periods repeat (is the next rise due in four years?), and how do the past peaks and quiet periods compare with now? Answer: no fixed cycle (gaps between bear-market peaks since 1974 run from 8 months to 14 years), but a repeating backdrop: every earlier big peak came with negative real rates and was followed by rising real rates; the 2026 peak is the first with positive real rates.

- `gold_cycles_since_1975.pdf`: the note (3 pages)
- `data/`: snapshot used (`gold_monthly_datahub.csv` monthly averages since 1833 from the World Gold Council / LBMA via datahub.io, `gc_daily.csv` COMEX futures from the 19 Nov snapshot, `fred_monthly.csv` CPI and 10-year yields, `fred_dfii10_daily.csv` TIPS yields)
- `cycles.json`, `monthly.csv`: outputs of `analyse_cycles.py`
- `scripts/`: `fetch_history.py <dir>/data` -> `analyse_cycles.py <dir>` -> `build_cycles.py <dir> <out.pdf>`, run from `desk/`

Method: monthly averages throughout (November 2026 is the COMEX average to 19 Nov). Bear markets by the 20/20 rule on monthly averages. Real prices deflated by US CPI; the October 2025 CPI was never published and is interpolated. The pre-2003 real rate is the 10-year yield minus CPI inflation over the past year. Quiet periods are chosen by eye. With this few cycles the comparisons describe; they do not forecast.
