# Weekly gold desk

A separate project next to the paper. Every week it refits the gold volatility
model on the latest Friday close, logs the forecast, scores every forecast made
so far against what actually happened, and renders a desk note (PDF).

The forecast log only grows, so the track record maps more data every week.

## Layout

```
desk/
  gold_desk/          the package
    data.py           daily closes from Yahoo Finance (gold, silver, oil, 10Y, dollar, S&P 500, VIX)
    model.py          GARCH(1,1) with Student-t shocks; simulation starts from the next-day variance
    store.py          the forecast log
    backtest.py       scores every forecast: PIT, 90% range hits, Kupiec test
    summary.py        the numbers behind a note -> reports/<origin>/summary.json
    report.py         the PDF
  store/
    live.jsonl        forecasts made on the day; append-only, one line per week
    backfill.jsonl.gz forecasts reconstructed for every Friday since 2006 (regenerable)
  reports/<origin>/
    summary.json      computed numbers (written by `forecast`)
    news.json         news, reads and watch list (written by a person or agent)
    gold_desk_<origin>.pdf
  tests/
```

## The model

Same specification as the paper: GARCH(1,1), Student-t shocks, constant mean,
no drift in the simulation, 20,000 paths, seed 42, fitted on all daily GC=F
closes since 2003. One difference: the simulation starts from the one-step-ahead
variance, so the latest day's shock is included. The paper's `fit_garch` starts
from the variance of the last day itself, which is set before that day's move.

The model sizes moves. It does not forecast direction.

## Weekly protocol

Run on the weekend, after Friday's close (the routine runs Sunday 17:00 UTC).

```bash
cd desk
python -m pip install -r requirements.txt   # same interpreter for installing and running
python -m gold_desk forecast      # refit on the latest close, log it, score history, write summary.json
# write reports/<origin>/news.json (format below)
python -m gold_desk report        # render reports/<origin>/gold_desk_<origin>.pdf
python -m pytest -q
```

Prices come from Yahoo Finance, so the machine needs network access to
`query1.finance.yahoo.com`, `query2.finance.yahoo.com` and `fc.yahoo.com`.

`forecast` drops the current day while the New York session is still open, so
only finished closes enter the model. If you run it mid-week, the origin is the
last finished close and the note is a flash rather than a weekly note.

Other commands:

- `python -m gold_desk score` prints the coverage table.
- `python -m gold_desk backfill --start 2006-01-01 --end <date>` rebuilds the
  backfill (about 20 minutes). Live records are never overwritten.

## news.json

Everything except `bottom_line` is optional. Text may use `<b>` and `<i>`;
escape `&` as `&amp;`.

```json
{
  "title": "Desk note: weekly update",
  "bottom_line": "Two to four sentences: what happened, why, how it compares to last week's ranges, what matters next. Quote numbers from summary.json.",
  "day_notes": {"2026-10-28": "Fed holds at 3.75-4.00%; two dissents for a hike"},
  "reads": {"GC=F": "New 2026 low", "SI=F": "...", "CL=F": "...", "^TNX": "...",
            "DX-Y.NYB": "...", "^GSPC": "...", "^VIX": "..."},
  "extra_rows": [["Dec hike odds", "~85%", "~72%", "lower", "CME FedWatch, per press"]],
  "bullets": [{"title": "Fed", "text": "..."}],
  "levels": [3800, 4000],
  "watch_list": [["Fri 13 Nov: October CPI", "Why it matters"]],
  "sources": [{"name": "Kitco", "url": "https://..."}]
}
```

`levels` draws dotted lines on the charts and adds the chance of trading
through each level within a month to the note.

## Reading the track record

For each forecast and horizon (1, 5, 10 and 21 trading days) the realised close
gets a PIT value: its percentile in the forecast distribution. A calibrated
model puts 90% of closes inside its 90% range, 5% below and 5% above. The
Kupiec test checks whether the miss rate differs from 10%.

Weekly origins make the 1- and 5-day scores independent. The 10- and 21-day
windows overlap week to week, so their p-values are too optimistic.

## Drift

The model runs without drift. On 2 Nov 2026 six drift rules were tested on the
1,086 backfilled forecasts, each using only data up to its own date. Scores are
average quantile loss (about the CRPS); p-values come from a Diebold-Mariano
test with Newey-West errors.

| Drift | Per year | 1-month score | p | 1-week score | p |
|---|---|---|---|---|---|
| Half the expanding mean | +6% | -1.1% | 0.064 | -0.5% | 0.002 |
| Expanding mean | +12% | -1.1% | 0.36 | -0.7% | 0.027 |
| Mean of last 5 years | +9% | -1.1% | 0.35 | -0.6% | 0.058 |
| GARCH constant mean (MLE) | +19% | +0.6% | 0.75 | -0.6% | 0.27 |
| Momentum, last year | +11% | +0.2% | 0.90 | -0.4% | 0.49 |
| Momentum, last 3 months | +10% | +13.0% | 0.000 | +2.6% | 0.004 |

The switch rule was fixed before the test: drift goes in only if it improves the
1-month score with p < 0.05, improves it in both halves (2006-15 and 2016-26),
and does not worsen the 1-week score. Nothing passed. Short-term momentum is
significantly worse, which matches the paper: direction is not predictable.

The best candidate, half the expanding mean, is kept as a shadow test
(`backtest.drift_check`). Every weekly note re-scores it on the growing record
and says when it qualifies. Without drift the 1-month misses are lopsided (2.5%
below the range, 7.8% above); the shadow drift would make that 2.9% and 6.6%.

Backfilled forecasts use only data up to their own date, but today's data
vintage. Live forecasts record what was known on the day; they are the clean
out-of-sample record.
