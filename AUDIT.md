# Audit

Full audit before the results freeze and the paper brief.

| | |
|---|---|
| Date | 2026-10-13 |
| Commit audited | `dd582d4177aa7490d08e9d933e1119cb7a0aa6db` |
| Working tree | **dirty** — 6 modified, 5 untracked (see §1.3) |
| Data refetched | yes, cache cleared and rebuilt from source |
| Tests | 189 passed, 0 failed |
| Scripts | 14/14 run without error |

**Status: nothing non-trivial has been changed yet.** Two trivial fixes applied
(§6). Everything else is reported below and awaits your decision.

---

## 1. Project map

### 1.1 Data sources

Twelve series, **all USD-denominated**. No FX conversion exists anywhere in the
codebase, and none is needed.

| Series | Code | Source | Units | n | Range |
|---|---|---|---|---|---|
| gold_futures | `GC=F` | yfinance | USD/troy oz | 5,974 | 2003-01-02 → 2026-10-13 |
| silver_futures | `SI=F` | yfinance | USD/troy oz | 5,974 | 2003-01-02 → 2026-10-13 |
| sp500 | `^GSPC` | yfinance | index | 5,982 | 2003-01-02 → 2026-10-12 |
| vix | `^VIX` | yfinance | % annualised | 5,985 | 2003-01-02 → 2026-10-13 |
| dxy | `DX-Y.NYB` | yfinance | index | 5,998 | 2003-01-02 → 2026-10-13 |
| real_rate_10y | `DFII10` | FRED | % | 5,947 | 2003-01-02 → 2026-10-08 |
| usd_broad_index | `DTWEXBGS` | FRED | index | 5,203 | 2006-01-02 → 2026-10-02 |
| breakeven_inflation_10y | `T10YIE` | FRED | % | 5,948 | 2003-01-02 → 2026-10-09 |
| term_spread_10y2y | `T10Y2Y` | FRED | % | 5,948 | 2003-01-02 → 2026-10-09 |
| fed_funds_rate | `DFF` | FRED | % | 8,682 | 2003-01-01 → 2026-10-08 |
| fed_balance_sheet | `WALCL` | FRED | USD mn | 1,241 | 2003-01-01 → 2026-10-07 |
| high_yield_spread | `BAMLH0A0HYM2` | FRED | % | **786** | **2023-10-10** → 2026-10-08 |

Panel: 8,685 rows × 12 columns. Gaps are deliberately **not** filled.

Regressions use four drivers only: `real_rate_10y`, `usd_broad_index`,
`breakeven_inflation_10y`, `vix`.

### 1.2 Execution order

```
scripts/fetch_data.py            → data/cache/*.parquet
scripts/fase2_stationariteit.py  → ADF/KPSS
scripts/fase2_correlaties.py     → correlations, stability
scripts/fase3_regressie.py       → OLS/NW, VAR, ridge, walk-forward
scripts/fase4_simulatie.py       → GBM / GBM-t / GARCH-t, VaR/ES
scripts/fase4_figuren.py         → figures + Kupiec
scripts/valideer_buffer.py       → coverage benchmark, df sensitivity
scripts/pipeline.py              → end-to-end + run manifest
```

Library: `src/goldmodel/` — 24 modules, 7,670 lines. Tests: 12 files, 189 tests.
Scripts: 19 files, 6,668 lines.

### 1.3 Uncommitted work

The last session's work is **not committed**. `dd582d4` does **not** contain
`validation/`, `valideer_buffer.py`, `RESULTS.md`, `WALKTHROUGH.md`,
`test_validation.py`, the no-trade band, or the df standard error.

**For the paper this matters:** the commit hash in the appendix must refer to a
commit that actually contains the results. This needs committing before
Phase 2.

---

## 2. Reproduction

Cache cleared and refetched from FRED and yfinance; full suite and all scripts
rerun.

| Check | Result |
|---|---|
| Refetch | reproduces byte-identical panel shape (8,685 × 12) |
| Tests | **189 passed** |
| Scripts | **14/14 OK** — no errors |
| Phase 3 numbers | reproduce **exactly** |
| Coverage table | reproduces **exactly** |

### Numbers that moved (new data only, not code changes)

| Quantity | Stored | Now | Cause |
|---|---|---|---|
| Trading days | 5,959 | **5,973** | 3 more weeks of data |
| Gold price | $4,322.70 | **$4,202.50** | market moved |
| 99% buffer (pipeline) | 33.7% | **32.6%** | new data + price |
| Coverage table | — | identical | no new complete quarter |
| Phase 3 metrics | — | identical | walk-forward ends earlier |

Phase 3 reproduces exactly: directional accuracy **43.8%**, out-of-sample R²
**−0.0396**, RMSE **+1.96%** vs random walk, in-sample R² **0.1864**.

> **⚠ Superseded — see §9 (H3).** These figures reproduce, but they are
> *wrong*: they come from a `horizon=1, step=21` call that predicts 145
> disjoint days. Corrected: accuracy **51.9%**, R² **+0.0110**, RMSE
> **−0.55%**. This paragraph is left in place because treating
> reproducibility as evidence of correctness was itself the audit's biggest
> miss.

**Implication for the freeze:** the buffer number drifts with the data, so
Phase 2 must be a single atomic run with one timestamp, and the paper must
quote that run's date.

---

## 3. Correctness checks

### 3.1 Returns vs levels — PASS

All correlations and regressions use `build_change_panel`
([correlations.py:34](src/goldmodel/viz/correlations.py#L34)): log returns for
price series, first differences for rates and spreads. No regression on levels.
`fase2_correlaties.py` prints the spurious-regression warning explicitly.

### 3.2 Calendar, timezone, fake zero returns — PASS

| Series | n | Zero diffs | Verdict |
|---|---|---|---|
| gold_futures | 5,974 | 34 (0.57%) | normal for a liquid future |
| sp500 | 5,982 | 3 (0.05%) | fine |
| dxy | 5,998 | 74 (1.23%) | fine |
| real_rate_10y | 5,947 | 542 (**9.12%**) | stale TIPS quotes |
| breakeven_inflation_10y | 5,948 | 973 (**16.36%**) | stale TIPS quotes |
| fed_funds_rate | 8,682 | 6,333 (**72.95%**) | calendar-daily, policy constant |

Index is timezone-naive `datetime64[us]`, correct for daily data. **Zero
weekends in the gold series.** No forward-fill anywhere in the codebase
(verified by grep for `ffill`/`pad`/`reindex`).

See issues **M3** and **L1**.

### 3.3 Currency — PASS

Everything is USD. Gold is `GC=F` in USD/troy oz; the margin account is USD; no
EUR or local-currency leg exists. **No conversion to be inconsistent about.**

Worth stating in the paper: a European hedger would carry unhedged USD/EUR
exposure that this project does not model. That is a scope limitation, not an
error.

### 3.4 Look-ahead bias — PASS, verified by experiment

Code reading confirms drivers are lagged (`drivers.shift(1)`), train slices are
strictly before test slices, and ridge standardisation is fitted on training
data only ([models.py:265-295](src/goldmodel/models.py#L265)).

I did not rely on reading. Planted-signal test:

| Planted signal | Out-of-sample R² | Dir. accuracy | Expected |
|---|---|---|---|
| Pure noise | −0.0032 | 49.0% | ≈0 ✓ |
| In **yesterday's** driver | **+0.9609** | 93.1% | high ✓ |
| In **today's** driver | **−0.0022** | 49.2% | ≈0 ✓ |

The third row is the decisive one: a signal in the *contemporaneous* driver is
**not** detected, which is only possible if the lag is applied. If look-ahead
existed, that row would show high R².

Point-in-time integrity separately covered by
`test_point_in_time_integrity_across_all_dates`, which I verified fails against
a deliberately broken implementation.

### 3.5 Units and annualisation — PASS with one caveat

252 trading days throughout; `×252` for returns, `×√252` for volatility, Sharpe
SE as `1/√years`. Consistent across `backtest.py`, `simulate.py`, `signal.py`,
`spectral.py`.

Caveat: see **H1** (log returns compounded as simple) and **M4** (mixed units
across drivers).

### 3.6 Hard-coded numbers

| Value | Where | Provenance | Verdict |
|---|---|---|---|
| 1.0 bp total cost | `CostModel` | derived: 10¢ spread on $4,000 ≈ 0.25bp; set 4× higher deliberately | **justified, documented** |
| 5% initial margin | `MarginSettings` | CME convention | justified |
| 4.5% maintenance | `MarginSettings` | ~90% of initial, convention | justified |
| 99% confidence | throughout | the stated research question | justified |
| λ = 0.94 | `ewma_buffer` | RiskMetrics standard | justified |
| 504-day lookback | `rolling_percentile_buffer` | 2 years, stated | justified |
| 1,000-day burn-in | `build_quarter_starts` | GARCH needs history | justified, and its cost (94→78 quarters) is documented |
| 100 oz | `CONTRACT_SIZE_OUNCES` | COMEX contract spec | factual |
| `UNDERPOWERED` = 30 / 5 events | `coverage.py` | convention | justified; see **L2** |
| ridge α | `walk_forward_validate` | default, not tuned | **justified: not tuned on test data** |

No evidence of parameter tuning to fit. The 0.5σ signal threshold is documented
as deliberately un-optimised.

---

## 4. The key conceptual check: is this a hedge?

**This is the most important finding in the audit.**

### 4.1 What the project claims

The stated exposure is a **long physical gold** holding, offset by a short
futures position ([de_claim.md:148](docs/de_claim.md#L148),
[README.md:237](README.md#L237)): *"physical gold appreciates by as much as the
futures position loses."*

### 4.2 What the code actually models

`margin.py` models a **short gold futures position in isolation**. There is no
long leg, no portfolio, and no offsetting asset.

```
grep -l "hedge_ratio|minimum_variance|hedge_effectiveness|basis_risk" → none
```

**Finding: the hedge is asserted in prose and never modelled or tested.**

This does not invalidate the margin arithmetic — the cash required to survive
mark-to-market on a short future is correct regardless of what else you own.
But two claims in the docs are unsupported:

1. That the offset is exact. Physical bullion vs front-month futures carries
   **basis risk**, which is never quantified.
2. That the project is "about hedging" at all. As written it sizes liquidity
   for a **standalone short futures position**.

Severity **HIGH** — not a computational error but a framing error, and it is the
first thing an interviewer will probe.

### 4.3 Proper hedge tests (run for this audit, not previously in the project)

If the hedged exposure is physical gold, the test is trivially circular (gold
hedges gold; basis risk is the only question, and front-month continuous data
cannot measure it — **not computed**, needs multiple contract months).

So I tested gold as a hedge for the two exposures a reader would actually assume.
Daily log returns, n = 5,966, 2003-01-03 → 2026-10-12.

**Correlations, with bootstrap CIs (2,000 resamples):**

| Pair | ρ | 95% CI | Verdict |
|---|---|---|---|
| gold / S&P 500 | **+0.0284** | **[−0.0139, +0.0725]** | **includes zero** |
| gold / DXY | **−0.4042** | [−0.4308, −0.3760] | firmly negative |

**Stress periods — the test that matters for a hedge:**

| Period | n | ρ(gold, S&P) | ρ(gold, DXY) |
|---|---|---|---|
| 2008 GFC (Sep–Mar) | 146 | −0.0328 | −0.3169 |
| March 2020 | 24 | **+0.0720** | −0.3044 |
| 2022 bear market | 198 | +0.0253 | −0.3546 |
| Calm (VIX ≤ 16.9) | 2,985 | +0.0393 | −0.4349 |
| Volatile (VIX > 16.9) | 2,981 | +0.0260 | −0.3877 |

Gold does **not** become protective when equities fall. In March 2020 the
correlation was **positive**. The dollar relationship is stable across all
regimes.

**Minimum-variance hedge ratio and effectiveness:**

| Hedge | h* | Variance reduction (= R²) |
|---|---|---|
| S&P 500 hedged with gold | +0.0289 | **0.08%** |
| DXY hedged with gold | −0.1678 | **16.32%** |
| Gold hedged with DXY | −0.9724 | **16.32%** |

Out-of-sample (h* fitted on first half, applied to second):

| Hedge | h* | In-sample | Out-of-sample |
|---|---|---|---|
| S&P 500 / gold | +0.0096 | 0.01% | **0.09%** |
| Gold / DXY | −1.0008 | 17.66% | **14.47%** |

The dollar hedge ratio is stable (−0.97 → −1.00) and effectiveness survives
out-of-sample. The equity hedge is nothing, in-sample or out.

**Portfolio impact (full sample, correct log compounding):**

| Portfolio | Ann. return | Ann. vol | Max DD | CVaR(5%) |
|---|---|---|---|---|
| 100% S&P 500 | +9.51% | 18.66% | −56.78% | −2.90% |
| 95% / 5% gold | +9.59% | 17.78% | −54.43% | −2.75% |
| 90% / 10% gold | +9.67% | 16.94% | −51.95% | −2.62% |
| 80% / 20% gold | +9.83% | 15.47% | −46.92% | −2.37% |

In the worst drawdowns:

| Period | Portfolio | Max DD | CVaR(5%) |
|---|---|---|---|
| 2008 GFC | unhedged | −47.05% | −7.68% |
| 2008 GFC | 10% gold | −42.83% | −7.00% |
| March 2020 | unhedged | −33.92% | −11.38% |
| March 2020 | 10% gold | −31.30% | −10.50% |

**Interpretation — and the distinction matters.** Adding gold improves
volatility, drawdown and CVaR *without costing return*. But that is
**diversification**, not hedging: the benefit scales with the allocation and
comes from gold's own positive return plus near-zero correlation, not from gold
rising when equities fall. A hedge pays off *when the hedged asset falls*; in
March 2020 gold's correlation with equities was positive and the drawdown
improved by only 2.6 points on a 10% allocation.

### 4.4 Cost of carry — not modelled

`CostModel` covers commission, half-spread and slippage. It does **not** cover:

| Cost | Estimate | Status |
|---|---|---|
| Margin financing | 0.24–0.33% of notional per quarter at Fed funds 3.88% (on a 25–34% buffer) | **not in code** |
| Roll cost | ~4 bp per quarter (1–2 rolls × 2 trades × 1 bp) | **not in code** |
| Contango / backwardation | **not computed** — needs multiple contract months; front-month continuous cannot measure it | **not in code** |

The financing figure overstates the true cost, since margin balances usually
earn interest — the real cost is the spread, not the full rate.

**Roll effects, tested for this audit** (the README asserted they were "small
for gold"; this is the first time it has been checked):

| Window | n | Mean | Std | >3σ frequency |
|---|---|---|---|---|
| Roll days (25th → month end, pre-delivery) | 633 | +0.0274% | 1.100% | 1.1% |
| All other days | 5,340 | +0.0435% | 1.160% | 1.3% |

Mean difference p = 0.728, Levene variance p = 0.230. **The claim is
supported** — roll windows are statistically indistinguishable. This was
previously an assertion; it is now a measurement.

---

## 5. Issues

Severity: **HIGH** = affects a reported number or a headline claim ·
**MEDIUM** = affects interpretation · **LOW** = cosmetic or latent.

### H1 — Log returns compounded as simple returns · HIGH · **flagged, not fixed**

[backtest.py:138](src/goldmodel/backtest.py#L138): `equity = (1.0 + clean).cumprod()`

Inputs are **log** returns (`build_change_panel` uses `np.log(s/s.shift(1))`),
but equity is built as if they were simple returns. Correct is
`np.exp(clean.cumsum())`.

Measured impact on gold buy-and-hold over the full sample:

| Quantity | As coded | Correct | Actual price move |
|---|---|---|---|
| Total return | **714.3%** | **1,114.2%** | 1,114.2% ($346.10 → $4,202.50) |
| Max drawdown | **−48.37%** | **−44.36%** | — |

**Affected:** `total_return`, `max_drawdown`, `equity_curve()` — so the
−36.8% / −40.5% / −42.7% drawdowns in README.md and RESULTS.md are wrong.

**Not affected:** `annual_return`, `annual_volatility`, `sharpe`,
`sharpe_standard_error`, all placebo results. These are mean/std of the daily
series and never touch `cumprod`. **The headline Sharpe figures (−0.001 gross,
−0.163 net) and every conclusion drawn from them stand.**

Fix is one line plus updating the quoted drawdowns. I have not applied it
because it changes published numbers.

### H2 — "Hedge" is asserted, never modelled · HIGH · **flagged**

See §4. The code models a standalone short futures position; the hedge, its
ratio, its effectiveness and its basis risk are nowhere computed. Requires a
decision on framing (§7), not a code fix.

### M1 — Carry cost excluded from the hedge economics · MEDIUM · **flagged**

§4.4. Financing (~0.24–0.33%/quarter) and roll (~4bp/quarter) are omitted. Small
relative to a 25–34% buffer, but they are the recurring cost of the protection
and the project reports the benefit without them.

### M2 — Basis risk between physical and futures not quantified · MEDIUM · **not computable with current data**

The claimed offset (physical rises as futures fall) is exact only if basis is
constant. Measuring it needs spot or multiple contract months. **Not computed** —
would require a new data source.

### M3 — Stale quotes in two drivers · MEDIUM · **flagged**

`breakeven_inflation_10y` has 16.4% zero changes and `real_rate_10y` 9.1%.
Both are regression drivers. Stale quotes attenuate coefficients toward zero
(errors-in-variables), so the measured relationships are, if anything,
*understated*. This strengthens rather than weakens the negative result, but it
should be stated.

### M4 — Mixed units across drivers, undocumented · MEDIUM · **flagged**

Gold and USD are log returns; rates, breakevens, VIX are **level differences**
(percentage points). Coefficient magnitudes are therefore not comparable across
drivers. Defensible modelling, but nowhere documented, and the paper will
interpret coefficients.

### M5 — Uncommitted results · MEDIUM · **needs your action**

§1.3. The appendix commit hash must point at a commit containing the results.

### L1 — `high_yield_spread` truncated to 786 observations · LOW · **flagged**

Starts 2023-10-10, not 2003. **Not used in any analysis** (defined in config
only), so no result is affected — but it appears in the correlation matrix,
where its ρ is computed on 3 years while others use 23. Either drop it or label
the differing n.

### L2 — `is_underpowered` boundary is floating-point fragile · LOW · **flagged**

`expected_breaches < 5.0` with `n=500, conf=0.99` gives 5.000000000000004, so
the flag is decided by float error at the boundary. Harmless here (actual N=78,
expected 0.78), but it should use a tolerance.

### L3 — `publication_lag_days` defined but unused · LOW · already documented

Walk-forward uses a hardcoded `shift(1)` instead of per-series lags. Already
disclosed in README limitations.

---

## 6. Trivial fixes applied

1. **`coverage.py` docstring** — stated "94 quarters" where the module tests 78.
   Added the reconciliation (94 = 5,959/63 arithmetic maximum; 78 = testable
   after the 1,000-day burn-in).
2. **README line-count claim** — said "roughly 3,500 lines of Python"; measured
   7,670 library + 3,515 test + 6,668 script. Corrected.

Both were done in the previous session and are listed for completeness.

---

## 7. Decisions I need from you

**1. H1 — fix the compounding bug?** One line. It changes published drawdowns
(−36.8% → roughly −34%, exact value after the fix). Sharpe figures unaffected.
My recommendation: **fix it**, and record it in the paper's learning-curve
section — it is a good example of a bug that leaves headline numbers intact
while corrupting secondary ones.

**2. H2 — how should the paper frame the hedge?** Three options:

- **(a) Reframe honestly as liquidity sizing for a standalone short futures
  position.** Most accurate to what the code does. Drops the word "hedge" from
  the claim. Smallest change, and defensible.
- **(b) Keep the physical-gold framing and add the basis-risk caveat.** Honest
  about the gap but leaves the central claim resting on an untested assumption.
- **(c) Add the gold-as-diversifier analysis from §4.3 as a second results
  section.** This is a genuine, well-identified negative result (gold is not an
  equity hedge: ρ = +0.028, CI includes zero, 0.08% variance reduction) plus a
  positive one (gold/USD, 14.5% out-of-sample variance reduction, stable h* ≈
  −1.0). It is the most interesting material in the audit and directly answers
  your item 4.

My recommendation: **(a) + (c)**. Reframe the margin work as liquidity sizing,
and add §4.3 as a second contribution. That gives the paper two clean findings
— one about predictability, one about hedging — both negative in the headline
and both properly tested.

**3. M1 — add carry costs to the model, or report them as an external
estimate?** Adding them properly means a financing model and roll calendar.
Reporting the ~0.24–0.33%/quarter estimate as a stated external figure is
cheaper and probably sufficient at this precision.

**4. M5 — shall I commit the current work** so the paper can cite a real hash?

**5. Scope for Phase 2:** should `results/key_numbers.json` include the §4.3
hedge analysis? It is currently computed only in this audit, not in any script.
If yes, it needs a script (`scripts/analyse_hedge.py`) so the numbers are
reproducible — per your rule that every number must be traceable to a
`results/` file.

---

## 8. Summary

Where the project is sound:

- **No look-ahead bias.** Verified by planted-signal experiment, not just code
  reading.
- **Returns not levels**, everywhere, with the spurious-regression warning
  printed.
- **Annualisation consistent** at 252 / √252.
- **Hard-coded values justified**, cost assumptions derived from the actual
  spread and set conservatively, no evidence of tuning to fit.
- **Reproducible**: refetch reproduces the panel; 189 tests pass; 14/14 scripts
  run; phase 3 numbers reproduce exactly.
- **Roll effects**, previously asserted to be small, are now measured and the
  assertion holds (p = 0.73).
- **Single currency**, so no conversion inconsistency is possible.

Where it needs work:

- **One real numerical bug** (H1), affecting drawdown and total return but not
  Sharpe or any conclusion.
- **One framing problem** (H2), which is the most consequential item here: the
  word "hedge" is doing work the code does not support.
- **Carry costs and basis risk** absent (M1, M2).
- **Two documentation gaps** (M3, M4) that affect how coefficients should be
  read.

The negative results — direction unpredictable, GARCH not beating a fixed rule,
gold not hedging equities — all survived the audit. The §4.3 hedge analysis is
new and is the strongest addition available to the paper.

---

## 9. Addendum (post-freeze): H3 — the phase-3 bug was never actually fixed

Found while freezing results, because `freeze_results.py` called
`walk_forward_validate` with the correct arguments and disagreed with every
published number.

### What happened

[fase3_regressie.py:182](scripts/fase3_regressie.py#L182) calls:

```python
walk_forward_validate(target, drivers, min_train=1000, step=21)
```

No `horizon` argument, so it takes the default `horizon=1`. **That is exactly
the bug `docs/WALKTHROUGH.md` presents as a worked example of a fixed
mistake.** It was fixed in `pipeline.py` and never in the script that produced
the published phase-3 numbers.

### The numbers

| Configuration | n_oos | R²_oos | Dir. accuracy | RMSE vs RW |
|---|---|---|---|---|
| `horizon=1, step=21` (what the docs quote) | **145** | **−0.0396** | **43.8%** | **+1.96%** |
| `horizon=21, step=21` (correct) | **3,024** | **+0.0110** | **51.9%** | **−0.55%** |

Every published phase-3 figure comes from the buggy configuration: 145 disjoint
days, not 3,024. The sign of the headline finding reverses.

### Does the conclusion survive? Yes — but the evidence does not

Significance of the corrected result (n = 3,024):

| Test | Value | Verdict |
|---|---|---|
| Diebold-Mariano, OLS vs random walk | DM = −1.371, **p = 0.170** | not significant |
| Directional accuracy | 51.65%, z = 1.82, **p = 0.072** | not significant at 5% |

So "macro data does not reliably predict gold direction" **still holds**. What
changes is the basis: the honest statement is *"no significant predictive
power, R² ≈ +0.01, p = 0.17"*, not *"worse than a coin flip at 43.8%"*.

The old numbers overstated the negative result. A 43.8% directional accuracy on
145 scattered days was noise being read as a finding.

### Affected files

Every one of these quotes the buggy figures:

- `docs/de_claim.md:47,49`
- `docs/fase3_resultaat.md:107,108,112,115`
- `docs/HET_HELE_VERHAAL.md:228,229,232`
- `docs/RESULTS.md`, `docs/WALKTHROUGH.md`, `README.md`
- `AUDIT.md:97` — my own §2, which reported these as "reproducing exactly".
  They did reproduce; the script reproduced its own bug.

### Severity

**HIGH.** Not because the conclusion flips — it does not — but because the
central claim was evidenced by a configuration the project itself documents as
wrong, and because my §2 called that reproduction a pass.

### Status

**Flagged, not fixed.** Fixing it means a one-line change to
`fase3_regressie.py` plus updating the phase-3 numbers in six documents. That
is a rewrite of the project's headline result and needs your decision first.

### Why the audit missed it initially

§2 checked that phase 3 *reproduced its stored numbers*. It did. Reproducibility
and correctness are different properties, and a script that deterministically
reproduces its own bug passes the first while failing the second. The only
reason it surfaced is that a second, independent implementation disagreed.
