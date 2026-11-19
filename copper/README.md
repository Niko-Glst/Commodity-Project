# Dr. Copper and the tech market

A side project next to the paper and the weekly gold desk. Copper is called "Dr. Copper" because it is
said to diagnose the economy before economists do. Since the AI build-out, copper also trades as an
input to data centres and power grids, so it is often mentioned in the same breath as the Nasdaq.
This project checks two things on data since 2000:

1. **Co-movement:** do copper and the tech market move together in the same week, and has that link
   become stronger in the AI era?
2. **Leading indicator:** does copper's past move help forecast the Nasdaq's next move?

The two are different. Copper can move with the Nasdaq every week and still be useless as an
indicator, because an indicator has to be known before the move.

## Data

Daily closes from Yahoo Finance since 2000 (`data/prices.csv`, the snapshot used):
COMEX copper (HG=F) and gold (GC=F) futures, Nasdaq Composite, Nasdaq-100, PHLX Semiconductor (SOX),
S&P 500, US 10-year yield, dollar index, Freeport-McMoRan and the Global X Copper Miners ETF (COPX).

## Pre-registered test (fixed 19 Nov 2026, before the first run)

Copper counts as a leading indicator for the Nasdaq only if one of three candidate signals passes
all three conditions:

| Candidate signal | Known at the origin |
|---|---|
| Copper, past 4 weeks (log return) | yes: measured up to the day before |
| Copper, past 13 weeks | yes |
| Copper/gold ratio, past 13 weeks | yes |

- **Target:** the Nasdaq Composite's log return over the next 4 weeks, from each weekly close.
- **Forecast:** an OLS regression of the target on the signal, refitted every week on the pairs whose
  outcome was already known (expanding window, first forecast after five years of pairs).
- **Benchmark:** the expanding historical mean of the target.
- **Rule:** out-of-sample R² above zero, a one-sided Clark-West p-value below 0.05 / 3 = 0.0167
  (Bonferroni for three candidates; Newey-West errors with 3 lags for the overlapping 4-week
  windows), and R² above zero in both halves of the evaluation period.

The signal is measured up to the trading day **before** each origin. Yahoo's daily copper close
appears to be later than the 13:00 ET settlement (on 9 Sep 2026 Yahoo shows $6.80; CNN reported a
record settlement of $6.89), so a same-day copper close could contain news from after the Nasdaq's
16:00 close. Skipping a day rules that out.

Reported next to the rule, not part of it: the same test for the Nasdaq-100 and SOX, a 13-week horizon,
and the reverse direction (does the Nasdaq lead copper?).

Before fixing the rule, only descriptive numbers were looked at (price levels, peaks and November
changes); no forecasting result had been computed.

## Result (19 Nov 2026, data to the 18 Nov close)

Note: [dr_copper_2026-11-18.pdf](reports/2026-11-18/dr_copper_2026-11-18.pdf); numbers in
[results.json](reports/2026-11-18/results.json).

**Copper is not a leading indicator for the Nasdaq.** None of the three candidates passes; all three
forecast worse than the plain historical average.

| Candidate signal | Forecasts | R² vs average | Clark-West p | R², 1st half | R², 2nd half |
|---|---|---|---|---|---|
| Copper, past 4 weeks | 1,098 | -0.82% | 0.58 | -0.57% | -1.07% |
| Copper, past 13 weeks | 1,089 | -0.46% | 0.25 | +0.10% | -1.01% |
| Copper/gold ratio, past 13 weeks | 1,089 | -0.38% | 0.28 | +0.55% | -1.30% |

The side checks agree: no copper signal helps for the Nasdaq-100 or SOX or at 13 weeks, the reverse
direction (Nasdaq or SOX leading copper) does not pass either, and the Nasdaq's next four weeks after a
13-week copper fall are no different from those after a rise (p = 0.63).

**They do move together.** The weekly correlation with the Nasdaq Composite is 0.59 over the past 52
weeks, the highest since March 2021 (peak 0.71 in 2012). By era: 0.22 (2000-07), 0.53 (2008-09),
0.41 (2010-19), 0.39 (2020-22), 0.35 (2023-26). The AI era is not more linked than 2010-19 (p = 0.35).

**Dr. Copper and yields.** The copper/gold ratio tracks the 10-year yield in 13-week changes (0.50 since
2000, 0.37 since 2023), but since 2023 the levels have split (-0.28) because of gold's rally.

## Layout

```
copper/
  dr_copper/
    data.py       daily closes from Yahoo Finance, snapshot in data/prices.csv
    analysis.py   weekly returns, correlations by era, the out-of-sample test, bear markets
    report.py     the PDF
  data/           the price snapshot used
  reports/<last close>/
    results.json  every number in the note
    dr_copper_<date>.pdf
  tests/
```

## Running

```bash
cd copper
python -m pip install -r requirements.txt
python -m dr_copper fetch     # refresh data/prices.csv (skip to reuse the snapshot)
python -m dr_copper test      # pre-registered test and side analyses -> reports/<last close>/results.json
python -m dr_copper report    # the PDF
python -m pytest -q
```
