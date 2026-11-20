# Weekly gold desk

A separate project next to the paper. Every week it refits the gold volatility
model on the latest Friday close, logs the forecast, scores every forecast made
so far against what actually happened, and renders a desk note (PDF).

The forecast log only grows, so the track record maps more data every week.

## Notes so far

| Date | Note | Type |
|---|---|---|
| 26 Oct 2026 | [gold_desk_note_2026-10-26.pdf](reports/2026-10-26/gold_desk_note_2026-10-26.pdf) | One-off: volatility and range review since 8 Oct |
| 30 Oct 2026 | [gold_desk_2026-10-30.pdf](reports/2026-10-30/gold_desk_2026-10-30.pdf) | Weekly, Friday close |
| 2 Nov 2026 | [gold_desk_note_2026-11-02.pdf](reports/2026-11-02/gold_desk_note_2026-11-02.pdf) | One-off: Monday update, 08:30 ET |
| 12 Nov 2026 | [gold_desk_intraday_2026-11-12.pdf](reports/2026-11-12/gold_desk_intraday_2026-11-12.pdf) | One-off: intraday sell-off and volatility clustering ([README](reports/2026-11-12/README.md)) |
| 13 Nov 2026 | [gold_desk_2026-11-13.pdf](reports/2026-11-13/gold_desk_2026-11-13.pdf) | Weekly, Friday close (covers two weeks: no weekly forecast was logged on 6 Nov); first rolling-window test |
| 18 Nov 2026 | [gold_desk_flash_2026-11-18.pdf](reports/2026-11-18/gold_desk_flash_2026-11-18.pdf) | One-off: overnight break below $3,800, against the 13 Nov forecast ([README](reports/2026-11-18/README.md)) |
| 19 Nov 2026 | [gold_desk_summary_2026-11-19.pdf](reports/2026-11-19/gold_desk_summary_2026-11-19.pdf) | One-off: why gold is falling (Fed minutes, real yields, dollar, de-risking) ([README](reports/2026-11-19/README.md)) |
| 19 Nov 2026 | [gold_cycles_since_1975.pdf](reports/2026-11-19-cycles/gold_cycles_since_1975.pdf) | One-off: gold's peaks and quiet periods since 1975 compared with now ([README](reports/2026-11-19-cycles/README.md)) |
| 20 Nov 2026 | [gold_report_2026-11-20.pdf](reports/2026-11-20/gold_report_2026-11-20.pdf) | Full report: the 2026 sell-off, macro, flows, past peaks, all tests, 14 number checks ([README](reports/2026-11-20/README.md)) |

Each note has its own folder `reports/<date>/` with the numbers behind it.
Weekly notes add a row here; one-off notes also carry their data snapshot and
scripts, because intraday data cannot be fetched again later.

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
  reports/<origin>/    one folder per note (see "Notes so far")
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
- `python -m gold_desk window-check --end <date>` scores rolling estimation
  windows against the full sample (about 15 minutes) and writes
  `reports/<date>/window_check.json`; run it before `forecast` and the note
  shows the result.
- `python -m gold_desk iv-check` scores GVZ implied volatility against the
  stored GARCH forecasts (seconds; it rescales stored quantiles) and writes
  `reports/<last live origin>/iv_check.json`.

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

## Rolling estimation window

The model is fitted on every close since 2003. On 16 Nov 2026 two rolling
samples, the last 10 and the last 5 years of daily returns, were scored
against that full sample on every weekly origin where they had enough data,
with the same seed (common random numbers). The switch rule was fixed before
the run and has the same shape as the drift rule, with a Bonferroni level for
two candidates: a window goes in only if it improves the 1-month score with
p < 0.025, improves it in both halves of its sample (split at the median
origin), and does not worsen the 1-week score.

| Window | Origins from | 1-month score | p | 1-week score | p |
|---|---|---|---|---|---|
| Last 10 years | Jan 2013 (717) | -0.07% | 0.37 | -0.11% | 0.051 |
| Last 5 years | Jan 2008 (978) | +0.02% | 0.90 | -0.10% | 0.23 |

Neither qualifies: the differences are about a tenth of a percent. The model
stays on the full sample. Each weekly note shows what both windows would say
for the week ahead (`summary.json` `rolling`), so the comparison stays visible.

## Implied volatility (GVZ)

The GVZ is the CBOE's 30-day implied volatility of gold (GLD options), daily
since June 2008. On 17 Nov 2026 two ways of using it were tested on the 905
stored weekly forecasts from July 2009, after one year of history for the bias
correction. Both rescale the GARCH forecast so that its expected 1-month vol
hits a target; the shape (fat tails, volatility dynamics) stays GARCH. The rule
was committed before the run (`7728ef6`): same shape as the window rule, p <
0.025 for two candidates.

- The GVZ close of the day before the origin is used, because the GVZ closes
  after the COMEX settlement.
- Implied vol carries a risk premium. The bias correction is the median ratio
  of realised 21-day vol to the GVZ before it, over completed periods only
  (between 0.74 and 0.84).

| Candidate | 1-month score | p | 1-week score | p | Inside 90%, 1 month |
|---|---|---|---|---|---|
| GVZ, bias-corrected | +0.20% | 0.61 | -0.34% | 0.21 | 85% |
| Half GARCH, half GVZ | -0.16% | 0.41 | -0.42% | 0.001 | 88% |
| GARCH alone (used) | | | | | 90% |

Neither qualifies. The blend does improve the 1-week score significantly and
in both halves, but not the 1-month score, which is the horizon the rule is
about. Both candidates make the ranges too narrow: the median-based correction
takes off more premium than the data support. Changing the correction now,
after seeing the result, would be fitting to this sample, so the 1-week gain
stays a lead for a test on new live data rather than a reason to switch.

Backfilled forecasts use only data up to their own date, but today's data
vintage. Live forecasts record what was known on the day; they are the clean
out-of-sample record.
