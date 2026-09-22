# Gold Price Risk Model

**Quantitative analysis of gold futures: macro drivers, forecast validation, and
Monte Carlo margin sizing.**

*Nederlandse versie: [README.nl.md](README.nl.md)*

---

## The question this answers

> I hold a short gold futures position as a hedge for one quarter. How much
> liquidity must I keep available so that, with 99% confidence, I do not miss a
> margin call?

An existing hedging tool answers this with a rule of thumb: **5–10% of notional**.
This project replaces that with a number derived from data, together with an
explicit statement of how uncertain that number is.

**Headline result:** for a one-quarter horizon, 5% covers 44% of simulated paths
and 10% covers 69%. Reaching 99% confidence requires roughly **26–34% of
notional**, depending on the volatility model — and that range is itself the
finding, not a defect.

---

## What this project is *not*

This section comes first because it matters more than the results.

- **Not trading advice.** Nothing here is a basis for a financial decision.
- **Not a point forecast.** The simulation produces a probability distribution,
  never a single predicted price.
- **Not a claim that gold returns are predictable.** The null hypothesis was that
  a random walk cannot be beaten. Phase 3 confirms it, and that is reported as
  the result.
- **Not a production system.** It is a learning and portfolio project built to
  demonstrate methodology.

What it *is*: an honest, defensible analysis in which every methodological choice
is made explicit and justified — including the choices that make the result
*less* impressive.

---

## Headline findings

| # | Finding | Evidence |
|---|---|---|
| 1 | Returns have fat tails | Excess kurtosis **6.05**; **79** days beyond 3σ where a normal distribution predicts **16** |
| 2 | Losses are more extreme than gains | Skewness **−0.49** |
| 3 | Volatility clusters and persists | GARCH persistence **0.9956**, half-life **156 days** |
| 4 | There is no cycle in volatility | Spectral peak at 64 days explains **0.8%** of variance, fails out-of-sample |
| 5 | Macro relationships are weak | Strongest single driver explains **16%** of daily variance |
| 6 | Macro relationships are unstable | **4 of 5** drivers change sign over time (S&P 500: −0.33 to +0.43) |
| 7 | Gold is not a daily safe haven | Gold–VIX correlation **−0.02** across the full period *and every sub-period*, including the 2020 crash |
| 8 | Direction is not predictable | Out-of-sample R² **−0.04**; directional accuracy **43.8%** (below coin-flip) |
| 9 | Magnitude *is* predictable | This is what the margin model exploits |

**The central contrast:** direction is unpredictable, magnitude is not. A margin
calculation only requires the second.

---

## Methodology

### Phase 1 — Data layer and distributional analysis

- 12 series from FRED and Yahoo Finance, 2003–present (**5,957** trading days)
- Every series carries an economic rationale and a **pre-registered expected
  sign** in [`config.py`](src/goldmodel/config.py) — a discipline against
  post-hoc rationalisation
- Parquet cache with TTL, stale fallback, and per-series graceful degradation
- Revision behaviour classified per series and **verified against ALFRED**: the
  broad dollar index *is* revised (1.4% average, from a 2019 rebasing), which
  largely cancels in log returns but disproved the original "never revised"
  claim
- **Analyses run on the revised series, not point-in-time vintages.**
  `fetch_as_known_on()` is implemented but not yet wired into the walk-forward —
  a stated limitation, not an assumption

### Phase 2 — Stationarity and relationship stability

- **Spurious regression quantified:** on price levels, OLS finds a "significant"
  relationship in **92%** of 400 trials on *independent random walks*. On
  differences: 4%, as it should be.
- ADF and KPSS on all series — opposing null hypotheses, so they can corroborate
  or contradict each other. Ten of twelve series are non-stationary in levels.
- Rolling correlations (252-day window) expose the instability that a
  full-period average hides.
- VIF per driver to make multicollinearity visible.

### Phase 3 — Regression with honest validation

- OLS with **Newey-West** standard errors, because residuals are
  heteroskedastic and autocorrelated. The correction inflates standard errors by
  **1.66–1.81×**; one driver moves from significant to insignificant.
- **Walk-forward validation:** train to day *t*, predict *t+1*, roll forward.
  Drivers lagged one day. Never trained on future data.
- Benchmark is a **random walk**. Result: OLS is **1.96% worse** on RMSE, with a
  negative out-of-sample R².
- **Diebold-Mariano** test to separate a real difference from noise: no
  significant difference.

### Phase 4 — Monte Carlo and margin sizing

Three models, each justified by an earlier measurement:

| Model | Fixes | 99% buffer | Expected Shortfall |
|---|---|---|---|
| GBM, normal shocks | — (reference) | 26.0% | 29.7% |
| GBM, Student-t (df 3.5) | fat tails (Phase 1) | 26.4% | 32.3% |
| **GARCH(1,1), t shocks** | also clustering (Phase 1) | **34.5%** | **44.9%** |

- Per path we measure **maximum adverse excursion** — the largest *intermediate*
  move against the position, because that is when a margin call arrives, not at
  expiry.
- **Drift is zero by default.** The historical mean of +0.043%/day is +2.7% per
  quarter and raises the 99% VaR by over 3 percentage points. Phase 3 showed
  direction is unpredictable, and the standard error of that mean is one third of
  the estimate itself. Including it would smuggle in a point forecast.

#### Validation against history, not just internal consistency

| Source | p50 | p95 | p99 | Deviation |
|---|---|---|---|---|
| **Historical (actual data)** | 6.7% | 21.3% | **29.3%** | — |
| GBM normal | 5.7% | 18.9% | 26.0% | −3.3 pp |
| GBM t | 5.3% | 18.6% | 26.4% | −3.0 pp |
| GARCH t | 6.1% | 22.3% | 34.5% | +5.2 pp |

Constant-volatility models **understate** the tail; GARCH **overstates** it.
Cause: persistence of 0.9956 is near-unit, so the long-run level is poorly
identified — GARCH estimates 20.8% annualised volatility where the data says
18.3%.

- **Kupiec proportion-of-failures test** across three horizons. All three models
  pass, but GARCH is best calibrated: on the sharpest test (495 windows),
  exactly 5 breaches against 5 expected, versus 9 for the normal model.

---

## The answer

At $4,379/oz, one contract (100 oz) is **$437,940** notional.

| Confidence | Buffer | USD |
|---|---|---|
| 50% | 6.1% | $26,554 |
| 95% | 22.3% | $97,751 |
| **99%** | **34.5%** | **$151,108** |
| 99.9% | 57.6% | $252,443 |

Reported as a **range**, because the models disagree and that disagreement is
informative:

- **Lower bound** (constant volatility): ~26%
- **Historically observed**: 29.3%
- **Upper bound** (GARCH, best calibrated): 34.5%

### The qualification that reframes the result

This is a **liquidity requirement, not a loss.** In a hedge, physical gold
appreciates by as much as the futures position loses; net wealth is unchanged.
The cash is needed only *at the moment* the broker calls.

A credit line against the collateral therefore does the same work as cash,
without the opportunity cost. "Access to 34.5%" is a materially different
requirement from "34.5% in cash".

---

## Errors found and corrected

Documented because finding them is what the validation layer is for.

| Error | Impact | How it surfaced |
|---|---|---|
| Claimed core series are never revised | Unfounded point-in-time claim | ALFRED shows 249 of 261 dollar-index observations were revised |
| `fetch_vintage_series` had never run against the API | A "tested" function that failed on real data | FRED rejects requests exceeding its vintage-date limit |
| Summed all margin deposits instead of the peak net outlay | Overstated quarterly buffer by ~5 pp | Net loss did not equal the price move |
| Reported the contemporaneous R² of 18.6% as if usable | Overstated predictability by a factor of 11 | Lagging the drivers dropped it to 1.7% |
| Claimed Kupiec rejected the normal model (p=0.045) | False finding | The p-value flipped with the random seed — Monte Carlo noise, not evidence |
| Used a shuffled null in the spectral test | Would have "found" a 1,483-day cycle | An AR(1) null preserving persistence removed it |
| Asserted adjusted R² penalises useless variables | Overstated its protection | Adding 50 noise columns *raised* adjusted R² |

Each is now covered by a regression test.

---

## Quality assurance

- **149 tests**, no network dependency (synthetic frames, temporary directories)
- **Positive controls throughout:** the walk-forward validator must *find* a
  planted signal (out-of-sample R² > 0.5); the Kupiec test must *reject* a
  miscalibrated model. Without these, "no signal found" carries no information.
- **Look-ahead guard:** a test replaces all data after day 1,500 with nonsense
  and asserts that earlier predictions are bit-identical.
- **Placebo runs:** replacing the drivers with persistence-matched random series
  yields a 5.0% false-positive rate against a nominal 5% — the design is
  correctly calibrated. The real R² of 0.186 exceeds all 200 placebo runs (max
  0.003).
- Fixed random seeds, so every reported figure is reproducible.

---

## Getting started

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1           # Windows
pip install -r requirements.txt

cp .env.example .env                  # add a free FRED API key
python scripts/check_setup.py         # verifies packages, key, connections, cache
```

Without a FRED key the project still runs on the Yahoo Finance series and reports
per series what succeeded.

### Reproducing the analysis

```bash
python scripts/fetch_data.py              # retrieve and cache data
python scripts/plot_distributions.py      # Phase 1: distributional figures
python scripts/fase2_stationariteit.py    # Phase 2: ADF/KPSS, spurious regression
python scripts/fase2_correlaties.py       # Phase 2: correlations and stability
python scripts/fase3_regressie.py         # Phase 3: OLS, walk-forward, DM test
python scripts/fase4_simulatie.py         # Phase 4: Monte Carlo, VaR, ES
python scripts/fase4_figuren.py           # Phase 4: figures and Kupiec validation
python scripts/verken_vintage.py          # vintages, sample size, placebo runs
python -m pytest tests/ -q                # 139 tests
```

---

## Technical stack

`pandas` · `numpy` · `statsmodels` · `arch` (GARCH) · `scikit-learn` (ridge) ·
`scipy` · `pyarrow` · `matplotlib` · `pytest`

**Design notes.** Series definitions are data, not code — adding a driver is a
configuration change. The cache interface is deliberately narrow
(`load`/`save`/`is_fresh`) so a SQLite backend can replace Parquet when vintage
panels require querying. Docstrings and comments are in Dutch (the author's
working language); all identifiers are in English.

---

## Repository layout

```
src/goldmodel/
  config.py          series definitions: economic rationale + expected sign
  margin.py          margin accounting and buffer requirement
  models.py          OLS/Newey-West, walk-forward, Diebold-Mariano
  simulate.py        Monte Carlo, GARCH, VaR/ES, Kupiec
  data/              FRED + ALFRED, Yahoo, Parquet cache, loader
  viz/               figures per analysis layer
scripts/             one runnable script per analysis step
tests/               139 tests, including positive controls
docs/                findings per phase, concepts, backlog
output/figures/      23 figures, 20 in the main analysis (gitignored)
```

### Documentation

| Document | Contents |
|---|---|
| [HET_HELE_VERHAAL.md](docs/HET_HELE_VERHAAL.md) | the full narrative, zero to now |
| [fase2_resultaat.md](docs/fase2_resultaat.md) | stationarity, correlations, stability |
| [fase3_resultaat.md](docs/fase3_resultaat.md) | regression and walk-forward validation |
| [fase4_resultaat.md](docs/fase4_resultaat.md) | simulation, VaR, Kupiec, the answer |
| [r2_uitgelegd.md](docs/r2_uitgelegd.md) | why R² is 18.6%, 1.7%, and −0.04 |
| [drie_kritische_vragen.md](docs/drie_kritische_vragen.md) | vintages, sample size, placebo runs |
| [vintage_data.md](docs/vintage_data.md) | revisions, ALFRED, look-ahead bias |
| [begrippen.md](docs/begrippen.md) | every statistical concept, with references |
| [backlog/](docs/backlog/README.md) | proposals with the reason they are deferred |

Documentation is written in Dutch; this README summarises the findings in English.

---

## Known limitations

Stated explicitly rather than left for a reader to discover.

1. **Effective sample size is far below nominal.** 5,957 trading days, but only
   **94 non-overlapping quarters** — and realised volatility, the quantity Phase
   4 models, has an effective sample size of roughly **42** after correcting for
   autocorrelation. The GARCH parameters rest on that.
2. **No point-in-time data.** Analyses use the revised series. Measured impact
   on the dollar index is 1.4%, which largely cancels in log returns, but this is
   not a point-in-time backtest.
3. **The Kupiec test is weak at this sample size.** Even with 495 windows you
   expect only 5 breaches; the difference between 5 and 9 is not statistically
   separable.
4. **GARCH persistence of 0.9956 is near-unit.** The long-run variance is
   therefore poorly identified, which is why GARCH overstates the quarterly tail
   by roughly 5 pp.
5. **Differencing discards level information.** The arbitrage argument for real
   rates concerns levels; cointegration would address this and is not
   implemented. Documented in the backlog.
6. **Continuous front-month futures contain roll effects.** Small for gold (flat
   forward curve) but present.

7. **Unstable coefficients are reported, not solved.** Four of five drivers
   change sign over time; a regime-switching model is the logical next step and
   sits in the backlog.

---

## License and data sources

Educational project. Data from FRED (public domain) and Yahoo Finance (unofficial
source, no guarantees on accuracy or availability). Not investment advice.
