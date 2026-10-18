# Results

Every number below comes from `python scripts/pipeline.py` and
`python scripts/valideer_buffer.py`. Data: 5,959 daily observations of gold
futures and four macro drivers, 2003–2026.

---

## The claim, in one line

Gold's **direction** is not predictable from public macro data. Its
**magnitude** partly is, and that is enough to size a margin buffer.

---

## 1. Direction: not predictable

Walk-forward, 12 years, 3,024 out-of-sample trading days.

| Measure | Value | Benchmark |
|---|---|---|
| Directional accuracy | 51.9% | 50% = coin flip (p = 0.072, n.s.) |
| Out-of-sample R² | −0.040 | 0 = predicting zero |
| RMSE vs random walk | −0.55% | better, but Diebold-Mariano p = 0.170 |
| Diebold-Mariano | not significant | — |

Built into a strategy, with a 1-day execution lag and 1 bp round-trip costs:

| | Annual return | Sharpe | Max drawdown |
|---|---|---|---|
| Strategy (gross) | −0.02% | **−0.001** | −36.8% |
| Strategy (net) | −1.83% | **−0.163** | −40.5% |
| Buy & hold | +6.56% | +0.382 | −42.7% |

Three controls:

- **Sharpe significance.** Over 12 years the standard error of a Sharpe ratio
  is 0.289. You need **0.57** to distinguish it from zero. The strategy
  reaches −0.163.
- **Placebo.** Positions shuffled 200×. The real result sits at the **39th
  percentile** — inside the noise distribution.
- **Execution lag.** Enforced in code; `run_backtest` refuses a lag of zero.

**Conclusion: the market is efficient with respect to public daily macro data.
This is the null hypothesis, and it is not rejected.**

---

## 2. Magnitude: partly predictable

| Finding | Evidence |
|---|---|
| Volatility clusters | GARCH persistence 0.9956, half-life 156 days |
| Fat tails | kurtosis 6.05; 79 days beyond 3σ where normal predicts 16 |
| Tail thickness of the shocks | t-distribution, df = **4.80** (SE 0.30) |

The df estimate matters more than it looks. Fitting a t-distribution to raw
returns gives 3.54, which sits in the region where population kurtosis is
**infinite**. Estimating it jointly with GARCH gives 4.80, with a 95%
interval of [4.21, 5.39] — entirely above 4. The difference is that the raw
fit confuses volatility clustering with genuine tail thickness; the GARCH
term removes the clustering first.

### How much does that uncertainty matter?

99% buffer over one quarter, varying df and holding everything else fixed
(100,000 paths, common random numbers):

| df | Buffer | ES | Population kurtosis |
|---|---|---|---|
| 3.0 | 34.9% | 65.0% | infinite |
| 4.0 | 34.6% | 47.0% | infinite |
| 4.21 | 34.1% | 45.9% | 28.6 |
| **4.80** | **33.7%** | **43.7%** | **7.5** |
| 5.39 | 33.4% | 42.0% | 4.3 |
| 8.0 | 32.6% | 39.6% | 1.5 |

| Source of uncertainty | Effect on the buffer |
|---|---|
| df within its 95% interval | **0.7 pp** |
| df across the whole range [3, 8] | **2.3 pp** |
| Model choice (constant vol vs GARCH) | **8.5 pp** |

**Model uncertainty dominates parameter uncertainty by roughly a factor of
four.** Pushing df all the way to 3 — far outside the confidence interval —
moves the buffer by 2.3 points. Choosing between constant volatility and
GARCH moves it by 8.5.

---

## 3. Does the model beat a rule of thumb?

This is the test the claim lives or dies by. 78 non-overlapping quarters,
99% coverage, each buffer re-estimated using only prior data.

| Model | N | Breaches | Expected | Kupiec p | Christoffersen p | Mean buffer | Max buffer |
|---|---|---|---|---|---|---|---|
| GARCH-t | 78 | 1 | 0.78 | 0.810 | 0.871 | **28.7%** | 70.2% |
| Fixed 25% | 78 | 1 | 0.78 | 0.810 | 0.871 | **25.0%** | 25.0% |
| Rolling p99 (2y) | 78 | 6 | 0.78 | 0.000 | 0.314 | 21.6% | 33.0% |
| EWMA λ=0.94 | 78 | 2 | 0.78 | 0.246 | 0.744 | 25.5% | 78.8% |

The EWMA buffer uses the 99.5% normal quantile so that it covers the largest
move *during* the quarter, like the other rules. With the 99% quantile it
covered only the end-of-quarter move and failed by construction (5 breaches).

### The honest conclusion

**GARCH-t does not win.**

Three rules pass both tests: GARCH-t, the fixed 25% and EWMA. Only the rolling
percentile fails. The fixed rule is the cheapest of the three: 25.0% against
25.5% for EWMA and 28.7% for GARCH-t. On the stated criterion (win on coverage
*and* on average buffer size), the rule of thumb wins.

The parameters have not been adjusted to change this. Tuning until the
preferred model wins would measure my own degrees of freedom rather than the
model.

### What the model does do

One detail worth keeping, because it shows where the two rules differ:

| Quarter | Realised | GARCH-t asked | Fixed asked |
|---|---|---|---|
| 2025-07 | **28.2%** | 27.8% ✗ | 25.0% ✗ |
| 2011-07 | 23.4% | 24.1% ✓ | 25.0% ✓ |

In the worst quarter in the sample every rule was breached, GARCH-t included
(27.8% against 28.2%). In 2011 both GARCH-t and the fixed rule held. The
single GARCH-t breach is within Monte Carlo error: over 20 seeds at 20,000
paths its buffer for the 2025 quarter is 28.3% ± 0.6 pp and holds in 11 of
20. In an earlier version with 2,000 paths per quarter the breach fell in 2011
instead, so which quarter is breached is decided by simulation noise, not by
the model.

The GARCH buffer ranges from 16.9% to 70.2% (median 25.5%). It asks for less
than the fixed rule in 37 of 78 quarters and more in 41. Whether that
adaptivity is worth the extra 3.7 points on average cannot be settled with 78
quarters.

### Why none of this is conclusive — the power problem

At 78 quarters and a 99% threshold you expect **0.78 breaches**. With fewer
than a handful of expected events, no test can discriminate: 0, 1, 2 and 3
breaches are all consistent with the null hypothesis. `tests/test_validation.py`
contains a test that locks this in.

Every row in the table above is therefore labelled **UNDERPOWERED**. The
p-values are indicative, not decisive. "Passes the test" here mostly means
"is not rejected", which almost any model achieves at this sample size.

This is a limit of 23 years of data on a quarterly horizon, not of the setup.
Getting real power would need roughly 500 quarters — about 125 years.

---

## 4. What I would tell someone using this

For a quarterly gold futures hedge, hold **25–34%** of notional against
margin calls, not the customary 5–10% (which covered 44% and 69% of paths
respectively).

Within that range the choice is not statistically settled. The fixed 25% is
cheaper on average and simpler to defend. GARCH-t costs 3.7 points more and
adapts to conditions, but the backtest does not show that this pays off: in
the worst quarter observed every rule was breached.

The asymmetry argues for the conservative side: running short on margin
forces liquidation at precisely the worst moment, because that is when margin
runs short. But this is a **liquidity** question, not a loss question — a
credit line against the collateral does the same work as cash.

---

## Footnotes

**Turnover.** The strategy trades 181× per year. A no-trade band is available
as a config option (`NO_TRADE_BAND` in `scripts/pipeline.py`, default 0.0 =
off). It was run once across bands 0.05–1.0 and no value was selected to
improve the outcome:

| Band | Turnover/yr | Gross Sharpe | Net Sharpe |
|---|---|---|---|
| 0.00 | 181.0 | −0.001 | −0.163 |
| 0.10 | 179.9 | −0.003 | −0.163 |
| 0.25 | 174.5 | 0.015 | −0.140 |
| 1.00 | 102.3 | 0.085 | −0.003 |

The band barely helps, and the reason is the finding: the median daily
position change is 0.61 and the position **flips sign on 49% of days**.
Position autocorrelation is −0.025. The turnover is not small adjustments
being jittered — it is a near-random signal genuinely wanting a different
position every day. A band only helps when a position wants to stay put. Note
also that the drivers are daily market series (real rate, USD index,
breakevens, VIX), not stale monthly macro: they change on 77–100% of days.

**Sample size.** 5,959 trading days, but on the quarterly question that is 94
non-overlapping windows, of which **78 are testable** — the first 1,000 days
are consumed fitting the model before the first decision point. Effective
sample size on realised volatility, after correcting for autocorrelation, is
**42**.

**Revisions.** Market quotes are not revised. `DTWEXBGS` is: ALFRED shows
249 of 261 observations revised (mean 1.36%, from the March 2019 rebasing).
It is configured as `REVISED_MILD`. The walk-forward uses a hardcoded 1-day
shift rather than the per-series `publication_lag_days` — a known limitation,
documented rather than silently fixed.

**Reproducing.** `python scripts/pipeline.py` writes a manifest with seed,
git commit and package versions to `output/runs/`.
