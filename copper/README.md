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

## Layout

```
copper/
  dr_copper/
    data.py       daily closes from Yahoo Finance, snapshot in data/prices.csv
    analysis.py   weekly returns, correlations by era, the out-of-sample test
  data/           the price snapshot used
  tests/
```

## Running

```bash
cd copper
python -m pip install -r requirements.txt
python -m pytest -q
```
