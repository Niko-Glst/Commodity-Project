# Paper brief: gold futures, predictability, and margin liquidity

**Written for:** whoever drafts the LaTeX paper from this document, with no
access to the repository.

Everything needed to write the paper is below. Every number traces to
`results/key_numbers.json` or a named file in `results/`. Where something was
not computed, it says so and why — there are no placeholder values.

**Units convention.** Values in `key_numbers.json` are stored as fractions
(0.3696 = 36.96%). This document presents them as percentages where that reads
better. Correlations and R² are dimensionless.

---

## 1. One-paragraph summary

This study asks two questions about gold futures over 2003–2026 (n = 5,964
trading days). First: can public macroeconomic data predict gold returns?
Using walk-forward validation with a one-day publication lag over 3,024
out-of-sample days, the answer is no — out-of-sample R² is +0.011 against a
random-walk benchmark, but the Diebold-Mariano test gives p = 0.170 and
directional accuracy of 51.9% has a binomial p of 0.072. Neither is
distinguishable from zero. Second: given that returns are unpredictable in
direction but volatility is strongly persistent (GARCH(1,1) persistence
0.9956, half-life 158 days), how much liquidity must a short futures position
hold against margin calls? A GARCH(1,1)-t model gives a 99% quarterly buffer
of 37.0% of notional, against an industry rule of thumb of 5–10% that covers
only 42.6% and 68.1% of simulated paths. However, two findings qualify this
sharply: the buffer is **conditional on starting volatility**, ranging from
24.2% to 74.9% across starting states (R² = 0.988 on start-state variance),
and the GARCH model does **not** outperform a fixed 25% rule on
non-overlapping quarterly backtests (both: 1 breach, Kupiec p = 0.810; GARCH
mean buffer 28.7% vs 25.0%). **Verdict: gold's direction is not predictable
from public macro data, its volatility is, and a volatility model improves
margin sizing over a 5–10% rule of thumb but not demonstrably over a simple
fixed 25% — at a sample size where no such test has power.**

---

## 2. Research question and motivation

### The practical problem

A holder of physical gold who wants to hedge price risk can short COMEX gold
futures. Futures are marked to market daily: an adverse price move is debited
from the margin account that same day. If the account falls below the
maintenance margin, the broker issues a margin call, and failure to meet it
means forced liquidation — necessarily at the worst moment, since that is when
margin runs short.

The question is therefore **not** "how much will I lose?" but "how much cash
must I be able to produce, and when?" For a hedger, net wealth is roughly
unchanged — the physical holding appreciates as the futures position loses —
so this is a **liquidity** question, not a solvency one. A credit line against
the collateral serves the same purpose as cash.

Existing practice in the hedging tool that motivated this work uses a rule of
thumb: hold 5–10% of notional. That number has no stated derivation. The aim
here is to replace it with a measured figure, together with an explicit
account of how uncertain that figure is.

### Why gold is a candidate hedge, and what this study found instead

Gold is conventionally described as a hedge against equity risk, dollar
weakness, and inflation. **An important scoping note for the paper: the
project's margin analysis models a short gold futures position in isolation.
It does not model a hedged portfolio.** The claimed offset against physical
gold is asserted but not quantified, because measuring basis risk between
bullion and front-month futures requires spot or multi-contract data that was
not available (see §9).

Because "hedge" was doing unsupported work in the original framing, a separate
analysis (§6.4) tests gold directly as a hedge for the two exposures a reader
would assume: equities and the dollar. That analysis is a second, independent
contribution and produces a clean negative result for equities.

### What this study does not claim

No claim is made that gold returns can be profitably predicted. The evidence
points the other way, and a deliberately-constructed trading strategy is
reported **because** it fails, as a quantification of that failure (§6.2).

---

## 3. Hypotheses

Stated so each can be falsified by a named test.

| # | Hypothesis | Falsifying test | Outcome |
|---|---|---|---|
| H1 | Macro drivers (real rate, USD index, breakeven inflation, VIX) predict next-day gold returns out-of-sample | Walk-forward R² ≤ 0, or Diebold-Mariano p > 0.05 vs random walk | **Not supported** (R² +0.011, p = 0.170) |
| H2 | Gold returns are normally distributed | Jarque-Bera, excess kurtosis = 0 | **Rejected** (kurtosis 6.04, JB p < 10⁻³⁰⁰) |
| H3 | Gold volatility is persistent and therefore forecastable | GARCH α+β not distinguishable from 0 | **Supported** (α+β = 0.9956) |
| H4 | A 5–10% margin buffer achieves 99% coverage over a quarter | Simulated coverage ≥ 99% | **Rejected** (42.6% and 68.1%) |
| H5 | A GARCH-t buffer beats naive rules on coverage **and** capital efficiency | Loses to any benchmark on either criterion | **Not supported** (loses to fixed 25% on cost) |
| H6 | Gold hedges equity risk | Minimum-variance variance reduction ≈ 0, or correlation CI contains zero | **Rejected** (0.09% OOS reduction; ρ = +0.028, CI [−0.015, +0.072]) |
| H7 | Gold hedges dollar risk | As H6 | **Supported, modestly** (14.5% OOS reduction, h* ≈ −1.0) |

H1 and H5 are the two the project most wanted to be true. Both fail, and both
are reported as failures.

---

## 4. Data

### Sources and series

All data is **USD-denominated**. No FX conversion exists anywhere in the
analysis, and none is required. A non-USD hedger would carry additional
currency exposure that this study does not model (§9).

| Series | Ticker | Source | Units | n | Range |
|---|---|---|---|---|---|
| Gold futures (dependent) | `GC=F` | Yahoo Finance | USD/troy oz | 5,965 | 2003-01-02 → 2026-09-30 |
| 10y real rate | `DFII10` | FRED | percent | 5,941 | 2003-01-02 → 2026-09-30 |
| Broad USD index | `DTWEXBGS` | FRED | index | 5,201 | 2006-01-02 → 2026-09-30 |
| 10y breakeven inflation | `T10YIE` | FRED | percent | 5,941 | 2003-01-02 → 2026-09-30 |
| VIX | `^VIX` | Yahoo Finance | percent p.a. | 5,976 | 2003-01-02 → 2026-09-30 |
| S&P 500 | `^GSPC` | Yahoo Finance | index | 5,974 | 2003-01-02 → 2026-09-30 |
| Dollar index | `DX-Y.NYB` | Yahoo Finance | index | 5,989 | 2003-01-02 → 2026-09-30 |
| Silver futures | `SI=F` | Yahoo Finance | USD/troy oz | 5,965 | robustness only |
| Fed funds rate | `DFF` | FRED | percent | 8,674 | carry cost only |
| 10y–2y term spread | `T10Y2Y` | FRED | percent | 5,941 | descriptive only |
| Fed balance sheet | `WALCL` | FRED | USD mn | 1,240 | descriptive only |
| High-yield spread | `BAMLH0A0HYM2` | FRED | percent | **780** | **excluded** — see below |

The four regression drivers are the real rate, broad USD index, breakeven
inflation, and VIX. Choice was made ex ante on economic grounds (gold as a
zero-coupon real asset: opportunity cost, currency of denomination, inflation
expectations, risk appetite), not by selection on fit.

**Fixed end date.** All analysis truncates at **2026-09-30**, enforced in
`build_panel()` via `ANALYSIS_END_DATE`. This matters more than it sounds and
is itself a finding (§7.1).

### Cleaning and known data issues

1. **No forward-filling.** Gaps are left as NaN. Forward-filling a weekly
   series to daily frequency creates artificial autocorrelation. Verified
   absent by searching the codebase for `ffill`/`pad`/`reindex`.
2. **Returns, not levels.** Price series become log returns; rates and spreads
   become first differences. Regressing non-stationary levels on each other
   produces spurious relationships.
3. **Mixed units across drivers.** Gold and USD are log returns; rates,
   breakevens and VIX are percentage-point changes. **Coefficient magnitudes
   are therefore not comparable across drivers.** This is defensible modelling
   but should be stated when coefficients are interpreted.
4. **Stale quotes.** Breakeven inflation has 16.4% zero daily changes and the
   real rate 9.1%, reflecting illiquid TIPS quotes. This attenuates regression
   coefficients toward zero (errors-in-variables), meaning measured
   relationships are if anything *understated* — which strengthens rather than
   weakens the negative result in H1.
5. **High-yield spread excluded.** The cached series begins 2023-10-10 (780
   observations, not 23 years). It is defined in configuration but used in no
   analysis. Mentioned only so its absence is not read as an oversight.
6. **Fed funds is calendar-daily** (8,674 observations, 73% zero changes, since
   policy is held constant between meetings). Used only for the carry-cost
   estimate, never as a regression driver.
7. **Roll effects tested, not assumed.** `GC=F` is a continuous front-month
   contract, so roll dates could introduce artificial jumps. Tested: roll-window
   returns (n = 633, days 25–month end before delivery months) versus all
   others show no significant difference in mean (**p = 0.728**) or variance
   (**Levene p = 0.219**). The continuous series is usable.

### Timezone and calendar

The index is timezone-naive `datetime64`, correct for daily closing data. The
gold series contains **zero weekend observations**. FRED and Yahoo series are
joined on an outer date join; misalignment appears as NaN rather than as a
silently wrong value.

---

## 5. Methodology

### 5.1 Distributional analysis

Excess kurtosis, skewness, and Jarque-Bera on daily log returns
$r_t = \ln(P_t / P_{t-1})$. Purpose: establish whether a normal-shock model is
defensible. It is not, which motivates the Student-$t$ specification in §5.4.

### 5.2 Stationarity

ADF (null: unit root) and KPSS (null: stationarity) on both levels and
differences. Two tests with **opposing nulls** are used deliberately: agreement
is informative, disagreement flags an ambiguous case. Prices are
non-stationary in levels and stationary in log differences.

*Rejected alternative:* cointegration (Engle-Granger / Johansen). The
arbitrage argument linking gold to real rates concerns **levels**, which
differencing discards. Not implemented — a genuine limitation, documented
rather than hidden (§9).

### 5.3 Regression with honest validation

In-sample model, OLS with Newey-West HAC standard errors:

$$r_t^{\text{gold}} = \beta_0 + \sum_{k=1}^{4}\beta_k \, \Delta x_{k,t-1} + \varepsilon_t$$

Drivers are lagged one day because FRED publishes day-$t$ values on business
day $t+1$; using contemporaneous values would be look-ahead bias.

Newey-West is used because residuals are autocorrelated and heteroskedastic.
A measured caveat worth including in the paper: HAC standard errors inflate
only when **both** the driver and the error are serially correlated. On
white-noise drivers the inflation factor measured 0.95 (no effect); on
persistent AR(0.95) drivers, 2.21.

**Walk-forward validation** is the core of the design. Fit on the first 1,000
observations, predict the next 21 days, advance 21 days, refit, repeat. This
gives 144 folds and 3,024 continuous out-of-sample days. Benchmarks:

- **random walk** — predicts zero (the economically correct null)
- **historical mean** — predicts the training-sample mean
- **ridge** — regularised, as a multicollinearity check

Out-of-sample $R^2$ is computed against the zero-prediction benchmark, so a
negative value means "worse than predicting nothing."

Diebold-Mariano tests whether the RMSE difference against the random walk is
systematic:

$$DM = \frac{\bar{d}}{\sqrt{\widehat{\operatorname{Var}}(\bar{d})}}, \qquad d_t = e_{1,t}^2 - e_{2,t}^2$$

with Newey-West variance, since $d_t$ is itself autocorrelated.

*Rejected alternative:* a single train/test split. Walk-forward uses the data
more efficiently and reveals whether performance is stable over time rather
than an artefact of one split point.

**Critical implementation note for anyone reproducing this.** The horizon must
equal the step. With `horizon=1, step=21` the procedure predicts one day and
skips twenty, producing 145 *disjoint* days rather than 3,024 continuous ones.
This bug produced every published phase-3 number in an earlier version of this
project and reversed the sign of the headline result (§10). The function now
raises on `horizon < step`.

### 5.4 Monte Carlo simulation

Three nested models, each justified by a prior measurement:

**(a) GBM with normal shocks** — the textbook baseline:
$$r_t = \mu + \sigma z_t, \qquad z_t \sim \mathcal{N}(0,1)$$
Known to be wrong: §5.1 found excess kurtosis of 6.04.

**(b) GBM with Student-$t$ shocks** — fixes the tails, keeps constant
volatility:
$$r_t = \mu + \sigma \sqrt{\tfrac{\nu-2}{\nu}}\, t_\nu$$
The scaling preserves unit variance so the models stay comparable.

**(c) GARCH(1,1) with Student-$t$ shocks** — the preferred specification:
$$\sigma_t^2 = \omega + \alpha \varepsilon_{t-1}^2 + \beta \sigma_{t-1}^2, \qquad \varepsilon_t = \sigma_t \sqrt{\tfrac{\nu-2}{\nu}}\, t_\nu$$

$\nu$ is estimated **jointly with the GARCH parameters by maximum likelihood**,
not fitted separately to raw returns. This distinction is material: fitting
$t$ to raw returns gives $\nu = 3.54$, which lies in the region where
population kurtosis is **infinite**. Joint MLE gives $\nu = 4.79$ (SE 0.299,
95% CI [4.20, 5.37]), entirely above 4. The raw fit conflates volatility
clustering with genuine tail thickness; the GARCH term removes the clustering
first.

The quantity of interest is the **maximum adverse excursion** — the worst
cumulative move against the position at any point within the horizon, not the
terminal value. A margin call is triggered by the path, not the endpoint:

$$\text{MAE} = \max_{1 \le s \le H}\left[\exp\left(\textstyle\sum_{t=1}^{s} r_t\right) - 1\right] \text{ for a short position}$$

Horizon 63 trading days (one quarter), 20,000 paths, seed 42.

### 5.5 Coverage backtesting

A buffer claiming 99% coverage should be breached in about 1% of periods. Two
tests, because there are two distinct failure modes:

**Kupiec proportion-of-failures** — is the *count* right?
$$LR_{POF} = -2\ln\left[\frac{(1-p)^{N-x} p^x}{(1-\hat{p})^{N-x}\hat{p}^x}\right] \sim \chi^2_1$$

**Christoffersen independence** — is the *timing* independent? Five breaches
spread over twenty years differs from five in one month; clustering means the
model misses the dynamics even when the average is right. Built from the
transition counts $n_{00}, n_{01}, n_{10}, n_{11}$.

Benchmarked against three naive rules over **non-overlapping** quarters
(overlapping windows share data and would make the independence test
meaningless):

1. **Fixed 25%** of notional, regardless of conditions
2. **Rolling 2-year 99th percentile** of realised quarterly excursions
3. **EWMA (RiskMetrics, λ = 0.94)** with normal quantiles — deliberately
   embodying the two assumptions §5.1 rejected. The buffer is
   $\exp(z_{0.995}\,\hat\sigma_t\sqrt{63}) - 1$: by the reflection principle
   the 99.5% quantile of the end-of-quarter move covers the *maximum* move
   during the quarter in 99% of driftless paths, which is what every rule is
   tested against

Each buffer is re-estimated at every decision point using only prior data.

### 5.6 Signal, costs and placebo

To quantify the cost of trading a signal that does not exist, predictions are
mapped to positions proportionally, clipped to ±1, with:

- **one-day execution lag**, enforced in code (`run_backtest` raises on lag 0)
- **1 bp round-trip cost** (0.2 commission + 0.3 half-spread + 0.5 slippage),
  deliberately ~4× the realistic institutional cost for gold futures, where a
  10-cent spread on a $4,000 price is ≈0.25 bp
- **Sharpe standard error** reported alongside every Sharpe, as $1/\sqrt{T}$
- **placebo test**: positions shuffled through time, 200 iterations, the real
  result located within the resulting null distribution

### 5.7 Hedge effectiveness

Minimum-variance hedge ratio. Holding one unit of exposure $e$ and shorting
$h$ units of hedging instrument $x$:
$$\operatorname{Var}(e - hx) = \sigma_e^2 - 2h\sigma_{ex} + h^2\sigma_x^2$$
Minimising over $h$:
$$h^* = \frac{\operatorname{Cov}(e,x)}{\operatorname{Var}(x)}$$

which is the OLS beta. The variance reduction achieved equals the $R^2$ of
that regression — the standard measure of hedge effectiveness (Ederington
1979). Reported both in-sample and out-of-sample ($h^*$ fitted on the first
half, applied to the second).

Correlations carry **bootstrap** confidence intervals (2,000 resamples) rather
than analytic ones, because the analytic standard error assumes normality and
§5.1 rejected it.

Stress periods were chosen **ex ante** from known events (2008 GFC, March
2020, 2022 bear market), not searched for in the data.

---

## 6. Results

All values from `results/key_numbers.json` unless noted. Sample: 2003-01-02 to
2026-09-30 unless stated.

### 6.1 Gold returns are not normally distributed

| Quantity | Value | Unit |
|---|---|---|
| Trading days | 5,964 | days |
| Gold price, first → last | 346.10 → 4,186.70 | USD/troy oz |
| Total return | +1,109.7% | — |
| Annualised volatility | 18.33% | per year |
| Excess kurtosis | **6.038** | — (normal = 0) |
| Skewness | −0.491 | — |
| Jarque-Bera p | < 10⁻³⁰⁰ | p-value |
| Days beyond 3σ | **78** | days |
| Days beyond 3σ, normal expectation | **16.1** | days |

Observed 3σ days exceed the normal prediction by a factor of 4.8.

> **`results/figures/fig1_return_distribution.pdf`** — histogram of daily log
> returns with a fitted normal of identical mean and standard deviation,
> showing the excess mass in both tails.

### 6.2 Direction is not predictable

Walk-forward, 144 folds, **3,024 continuous out-of-sample days**:

| Model | RMSE | Directional accuracy | OOS R² | vs random walk |
|---|---|---|---|---|
| random walk | 0.010834 | — | 0.0000 | — |
| historical mean | 0.010834 | 52.2% | −0.0001 | +0.01% |
| **OLS** | **0.010774** | **51.9%** | **+0.0110** | **−0.55%** |
| ridge | 0.010774 | 51.9% | +0.0110 | −0.55% |

Significance — **this is the part that matters**:

| Test | Value | Interpretation |
|---|---|---|
| Diebold-Mariano, OLS vs random walk | DM = −1.371, **p = 0.1705** | not significant |
| Directional accuracy | 1,562 / 3,024 = 51.65%, **binomial p = 0.0718** | not significant at 5% |
| In-sample R² (same drivers) | **0.1867** (N = 5,147) | contrast with +0.011 OOS |

The in-sample versus out-of-sample gap (18.7% → 1.1%) is the central
illustration: the relationships are real in-sample and do not survive honest
validation.

> **`results/figures/fig3_oos_r2.pdf`** — out-of-sample R² by model, showing
> OLS and ridge marginally above zero and the historical mean marginally below.
> Table: **`results/tables/walk_forward_metrics.csv`**

**The trading strategy built on this signal** (reported because it fails):

| | Annual return | Sharpe | Max drawdown |
|---|---|---|---|
| Strategy, gross | −0.016% | **−0.0014** | −36.16% |
| Strategy, net of costs | −1.826% | **−0.1634** | −38.55% |

| Control | Value |
|---|---|
| Annual turnover | **181.0×** |
| Sign flips | **48.7% of days** |
| Position autocorrelation (lag 1) | **−0.0245** |
| Sharpe standard error | 0.2887 |
| Sharpe required for significance (5%, two-sided) | **0.566** |
| Sharpe t-statistic (net) | −0.566 |
| Significant? | **No** |
| Placebo percentile (200 shuffles) | **39th** |

The turnover deserves comment: it is not an implementation artefact. The
position changes sign on nearly half of all days with autocorrelation of
−0.025 — the signature of a signal with no persistent content. A no-trade band
was tested as a configuration option and reduces turnover only from 181.0 to
179.9 at a 0.10 band, because the position genuinely wants to be somewhere
different every day. Table in `docs/RESULTS.md`.

### 6.3 Volatility *is* predictable

| Parameter | Value |
|---|---|
| GARCH α | 0.03623 |
| GARCH β | 0.95938 |
| **Persistence (α+β)** | **0.99561** |
| **Half-life of a shock** | **157.6 trading days** |
| Degrees of freedom ν (joint MLE) | **4.786** (SE **0.299**) |
| 95% CI for ν | [4.20, 5.37] |
| Long-run volatility | 20.86% p.a. |
| Conditional volatility at 2026-09-30 | 22.60% p.a. |

Persistence near unity means today's volatility is highly informative about
next quarter's. This is the exploitable regularity, and it requires no
directional forecast.

> **`results/figures/fig2_volatility_clustering.pdf`** — 63-day rolling
> annualised volatility over the full sample, with the sample mean marked.

### 6.4 Gold is not an equity hedge (it is a diversifier)

Daily log returns, n = 5,959, 2003-01-03 → 2026-09-30.

| Pair | ρ | 95% bootstrap CI | Contains zero? |
|---|---|---|---|
| gold / S&P 500 | **+0.0284** | **[−0.0151, +0.0721]** | **Yes** |
| gold / DXY | **−0.4041** | [−0.4314, −0.3749] | No |

Stress and regime behaviour — the decisive test for a hedge:

| Period | ρ(gold, S&P 500) |
|---|---|
| Full sample | +0.0284 |
| 2008 GFC (Sep 2008 – Mar 2009) | −0.0328 |
| **March 2020** | **+0.0720** |
| 2022 bear market | +0.0253 |
| Calm regime (VIX ≤ median) | +0.0386 |
| Volatile regime (VIX > median) | +0.0261 |

Gold does not become protective when equities fall. In March 2020 the
correlation was **positive** — the putative hedge failed precisely when needed.

Hedge ratios and effectiveness:

| Hedge | h* (in-sample) | Variance reduction IS | h* (OOS) | **Variance reduction OOS** |
|---|---|---|---|---|
| S&P 500 hedged with gold | +0.0289 | 0.08% | +0.0094 | **0.09%** |
| Gold hedged with DXY | −0.9727 | 16.33% | −1.0019 | **14.46%** |
| DXY hedged with gold | −0.1679 | 16.33% | −0.1765 | **14.29%** |

The dollar hedge ratio is stable across sample halves (−0.97 → −1.00) and
effectiveness largely survives out-of-sample. The equity hedge is
indistinguishable from nothing.

> **`results/figures/fig5_gold_not_an_equity_hedge.pdf`** — gold/S&P 500
> correlation in the full sample and in three stress periods, showing no shift
> toward negative correlation under stress.

**Portfolio effect** (full sample, log returns compounded as $\exp(\sum r)$):

| Portfolio | Annual return | Annual vol | Max drawdown | CVaR(5%) |
|---|---|---|---|---|
| 100% S&P 500 | +9.43% | 18.67% | −56.78% | −2.90% |
| 95% / 5% gold | +9.51% | 17.78% | −54.43% | −2.76% |
| 90% / 10% gold | +9.59% | 16.95% | −51.95% | −2.62% |
| 80% / 20% gold | +9.76% | 15.48% | −46.92% | −2.37% |

| March 2020 | Max drawdown |
|---|---|
| Unhedged | −33.92% |
| 10% gold | −31.30% |

**Interpretation, and the distinction is the point.** Adding gold improves
volatility, drawdown and CVaR without costing return. But this is
**diversification**, not hedging: the benefit scales with the allocation and
derives from gold's own positive return combined with near-zero correlation —
not from gold rising when equities fall. A hedge pays off *conditional on* the
hedged asset falling; in March 2020 the correlation was positive and a 10%
allocation improved drawdown by only 2.6 percentage points.

### 6.5 The margin buffer

At 2026-09-30, gold at $4,186.70, one COMEX contract (100 oz) = $418,670
notional. 20,000 paths, seed 42, 63-day horizon.

| Quantity | Value |
|---|---|
| **99% buffer, GARCH-t** | **36.96%** of notional |
| Expected shortfall at 99% | 48.43% |
| 99% buffer, GBM-normal | 26.05% |
| Coverage of the 5% rule | **42.59%** of paths |
| Coverage of the 10% rule | **68.10%** of paths |

The rule of thumb is badly miscalibrated: 10% of notional covers roughly
two-thirds of quarterly paths, not 99%.

> **`results/figures/fig4_buffer_vs_rule_of_thumb.pdf`** — cumulative
> distribution of maximum adverse excursion over a quarter, with the 5% and 10%
> rules and the 99% buffer marked.

### 6.6 The buffer does not beat a fixed rule

78 non-overlapping quarters, each buffer re-estimated on prior data only:

| Model | N | Breaches | Expected | Kupiec p | Christoffersen p | Mean buffer | Max buffer |
|---|---|---|---|---|---|---|---|
| GARCH-t | 78 | 1 | 0.78 | 0.8104 | 0.8711 | **28.69%** | 70.2% |
| **Fixed 25%** | 78 | 1 | 0.78 | 0.8104 | 0.8711 | **25.00%** | 25.0% |
| Rolling p99 (2y) | 78 | 6 | 0.78 | 0.0001 | 0.3136 | 21.59% | 33.0% |
| EWMA λ=0.94 | 78 | 2 | 0.78 | 0.2460 | 0.7440 | 25.46% | 78.8% |

Table: **`results/tables/coverage_comparison.csv`**

Three rules pass both tests: GARCH-t, the fixed rule and EWMA. GARCH-t and the
fixed rule tie on breaches (1 each); EWMA has 2. Among the passing rules the
fixed rule is the cheapest and GARCH-t the most expensive: 3.7 percentage
points above the fixed rule and 3.2 above EWMA. **On the stated criterion —
win on coverage *and* on capital efficiency — the rule of thumb wins.** No
parameters were adjusted in response to this result.

Only the rolling percentile fails Kupiec. It systematically under-reserves
(mean buffer 21.59%), which at least confirms the test discriminates against a
genuinely miscalibrated rule. An earlier version of the EWMA rule used the 99%
quantile of the end-of-quarter move instead of the maximum during the quarter
and failed by construction (5 breaches, Kupiec p = 0.0013); that was a
measurement error in the benchmark, not a property of EWMA, and is corrected
(§5.5).

**The power problem, which governs every conclusion in this section.** At 78
quarters and a 99% threshold, the expected number of breaches is **0.78**. With
fewer than a handful of expected events, 0, 1, 2 and 3 breaches are all
consistent with the null. Every row is flagged `UNDERPOWERED`. "Passes the
test" here means little more than "is not rejected." Meaningful power would
require roughly 500 quarters — about 125 years.

---

## 7. Robustness checks

### 7.1 Sensitivity to the end date — the buffer is conditional

This began as a reproducibility annoyance and became a substantive finding.
Re-running identical code with only the end date changed:

| End date | n | Ann. vol | Persistence | **Start vol** | **99% buffer** |
|---|---|---|---|---|---|
| 2025-09-30 | 5,713 | 17.69% | 0.9950 | 16.1% | **25.3%** |
| 2025-12-31 | 5,777 | 17.80% | 0.9952 | 23.1% | **35.9%** |
| 2026-03-31 | 5,838 | 18.20% | 0.9959 | 38.2% | **65.9%** |
| 2026-06-30 | 5,900 | 18.28% | 0.9956 | 28.2% | **46.4%** |
| 2026-09-30 | 5,964 | 18.33% | 0.9956 | 22.6% | **37.0%** |
| 2026-10-13 | 5,973 | 18.32% | 0.9954 | 20.2% | **32.6%** |

A **40.6 percentage point** spread with no code change. Sample volatility
barely moves (17.7% → 18.3%) and persistence is flat.

The cause is not instability but design: GARCH initialises the simulation from
**the conditional variance on the final day**, and with persistence 0.9956 that
state barely decays over 63 days. A controlled experiment — same sample, same
parameters, varying only the starting variance — isolates it:

| Start vol (p.a.) | 99% buffer | ES 99% |
|---|---|---|
| 14.8% | 24.2% | 31.2% |
| 17.1% | 27.6% | 35.9% |
| 20.9% (= long-run) | **33.9%** | 44.3% |
| 22.6% (= 2026-09-30) | **36.9%** | 48.3% |
| 27.9% | 46.4% | 61.9% |
| 37.1% | 64.5% | 88.6% |
| 41.7% | **74.9%** | 104.1% |

Table: **`results/tables/buffer_conditional_on_start_state.csv`**

The controlled sweep reproduces the end-date observations to within 1.4
percentage points, and **R² = 0.988** of the buffer variation across end dates
is explained by the starting variance ratio.

**Consequence for how the result must be stated.** "The 99% buffer is 37%" is
not well-posed. The defensible statement is *"37% of notional, conditional on
22.6% annualised volatility at initiation"*, with a range of **24–75%** across
plausible starting states. A single headline number conceals the dominant
source of variation.

> **`results/figures/fig6_buffer_depends_on_start_state.pdf`** — buffer against
> starting volatility, overlaying the controlled sweep (the mechanism) with the
> six observed end dates (how it was discovered).

### 7.2 Sensitivity to the degrees of freedom

Holding all else fixed, 100,000 paths, common random numbers:

| ν | 99% buffer | ES 99% | Population kurtosis |
|---|---|---|---|
| 3.0 | 37.4% | 71.6% | infinite |
| 4.0 | 37.0% | 50.6% | infinite |
| 4.21 | 36.6% | 49.5% | 28.6 |
| **4.79** (MLE) | **36.96%** | 48.4% | 7.5 |
| 5.39 | 35.8% | 45.2% | 4.3 |
| 8.0 | 34.9% | 42.5% | 1.5 |

Table: **`results/tables/df_sensitivity.csv`**

| Source of uncertainty | Effect on the buffer |
|---|---|
| ν within its 95% CI | ~0.8 pp |
| ν across [3, 8] | **2.5 pp** |
| Model choice (GBM-normal → GARCH-t) | **10.9 pp** |
| **Starting volatility state** | **50.7 pp** |

**The ranking is the finding.** Parameter uncertainty in ν is the *least*
important source. Model choice matters ~4× more, and the starting state
matters ~20× more. Monotonicity was verified at 100,000 paths; at 2,000 paths
the ordering breaks, confirming that the earlier figure was Monte Carlo noise
rather than signal.

### 7.3 Robustness checks not performed

Stated explicitly rather than implied:

- **Frequency.** All analysis is daily. Weekly or monthly aggregation was not
  systematically tested for the buffer. **Not computed.**
- **Currency.** Everything is USD. A EUR-based hedger's currency leg was not
  modelled. **Not computed.**
- **Alternative volatility models.** EGARCH, GJR-GARCH (asymmetry) and
  stochastic volatility were not fitted. Given that asymmetry is well
  documented in equity volatility, this is a real gap. **Not computed.**
- **Subsample stability of the GARCH parameters.** Persistence was observed
  across six end dates (0.9950–0.9959) but no formal structural-break test was
  run. **Not computed.**

---

## 8. Conclusions

### What the evidence supports

1. **Gold's daily direction is not predictable from these four public macro
   drivers.** Out-of-sample R² +0.011 with Diebold-Mariano p = 0.170;
   directional accuracy 51.9% with binomial p = 0.072. The honest statement is
   *"no detectable predictive power at this sample size"*, not *"predicts
   worse than chance."*
2. **The in-sample/out-of-sample gap is large and instructive.** R² falls from
   0.187 to 0.011 for the same drivers on the same data.
3. **A signal of this magnitude cannot survive transaction costs.** Gross
   Sharpe −0.001 becomes net −0.163 at 181× annual turnover; 12 years of data
   would require a Sharpe of 0.566 to distinguish from zero.
4. **Gold volatility is strongly persistent** (α+β = 0.9956, half-life 158
   days) and the shock distribution has finite but heavy tails (ν = 4.79,
   SE 0.299).
5. **The 5–10% rule of thumb is badly miscalibrated** for a quarterly horizon,
   covering 42.6% and 68.1% of paths against a nominal 99%.
6. **Gold is not an equity hedge.** Correlation +0.028 with a CI containing
   zero, 0.09% out-of-sample variance reduction, and positive correlation in
   March 2020. It is a *diversifier*: a 10% allocation cut portfolio volatility
   from 18.7% to 17.0% and max drawdown from −56.8% to −52.0% at no cost in
   return.
7. **Gold is a modest dollar hedge**: 14.5% out-of-sample variance reduction
   with a stable hedge ratio near −1.0.

### What the evidence does not support

1. **That GARCH beats a simple fixed rule for margin sizing.** It ties on
   breaches and costs 3.7pp more capital. H5 fails.
2. **That any of the coverage comparisons are conclusive.** At 0.78 expected
   breaches, the tests lack power. This is a limitation of 23 years of data on
   a quarterly horizon, not of the design.
3. **That a single buffer number is meaningful.** The starting volatility state
   moves it by 50 percentage points — far more than model or parameter
   uncertainty combined.
4. **That the margin analysis describes a hedge.** It models a standalone short
   futures position. Basis risk against physical gold is **not computed**.

### Practical implication

For a quarterly short gold futures position, hold **25–37% of notional**
against margin calls rather than 5–10% — and scale within that range by
current volatility, since the requirement rises by roughly 1.9 percentage
points of buffer per percentage point of annualised starting volatility
(OLS slope across `buffer_conditional_on_start_state.csv`).

Within that range the choice between a fixed 25% and a GARCH-conditional
buffer is **not statistically settled** at this sample size. The fixed rule is
cheaper on average and simpler to defend; the GARCH rule adapts to the
volatility state, but the backtest does not show that this pays off. In the
worst quarter observed (21 July – 16 October 2025, realised adverse move
28.2%) every rule was breached, GARCH-t included with a buffer of 27.8%.
That outcome is within Monte Carlo error: over 20 seeds at 20,000 paths the
GARCH-t buffer for that quarter is 28.3% ± 0.6 pp (standard deviation) and
holds in 11 of 20. The backtest estimates every GARCH-t buffer from 20,000
paths per quarter (seed 42 plus the quarter index), the same number as the
headline simulations; at 2,000 paths the noise was about 1.3 pp, enough to
decide which quarter was breached.

The asymmetry of the loss function argues for the conservative side: running
short on margin forces liquidation at the worst possible moment. But because
this is a liquidity rather than a solvency requirement, a committed credit
line against the collateral serves as well as cash — which converts the
question from *"do I hold 37%?"* to *"can I draw 37%?"*, a materially easier
requirement.

Carry cost of the protection: approximately **0.24–0.33% of notional per
quarter** in financing (at a 3.88% Fed funds rate on a 25–34% buffer; an upper
bound, since margin balances typically earn interest) plus roughly **4 bp per
quarter** in roll costs.

---

## 9. Limitations

Specific, and in rough order of how much they constrain the conclusions.

1. **The buffer is conditional, and the conditioning variable dominates.** The
   starting volatility state moves the result by 50.7pp against 10.9pp for
   model choice and 2.5pp for parameter uncertainty. Any single reported figure
   is incomplete without its starting state.
2. **The coverage tests are underpowered.** 78 non-overlapping quarters at 99%
   gives 0.78 expected breaches. No model comparison at this horizon can be
   decisive. Meaningful power needs ~125 years.
3. **Effective sample size is far below nominal.** 5,964 trading days, but 94
   non-overlapping quarters arithmetically and **78 testable** after the
   1,000-day burn-in. Realised volatility — the quantity actually being
   modelled — has an effective sample size of **42** after autocorrelation
   correction. The GARCH parameters rest on that.
4. **This is not a hedge analysis.** The margin work models a standalone short
   futures position. Basis risk between physical bullion and front-month
   futures is **not computed** — it requires spot or multi-contract data.
5. **GARCH persistence of 0.9956 is near-unit.** The long-run variance is
   therefore poorly identified, and the model's unconditional volatility
   (20.9%) exceeds the sample figure (18.3%).
6. **No regime breaks.** GARCH parameters are estimated on 23 years of history.
   An event qualitatively unlike anything in that window — a return to a gold
   standard, coordinated central-bank sales, an exchange failure — is by
   construction absent.
7. **No point-in-time data in the analyses.** The ALFRED machinery exists and
   is tested (a test verifies that a series requested as-of date *T* never
   contains a revision published after *T*, and it fails against a
   deliberately broken implementation), but the pipeline uses revised series.
   Measured revision impact on the dollar index is 1.4%, which largely cancels
   in log returns. The per-series `publication_lag_days` field is defined but
   unused; a hardcoded one-day shift is applied instead.
8. **Differencing discards level information.** The arbitrage argument linking
   gold to real rates concerns levels. Cointegration is not implemented.
9. **Mixed units across regression drivers** make coefficient magnitudes
   non-comparable (§4).
10. **Unstable coefficients are reported, not solved.** Four of five drivers
    change sign over subsamples; a regime-switching model is the logical next
    step.
11. **Single asset, single currency, single venue.** COMEX gold in USD. No
    cross-sectional or cross-market validation.

---

## 10. Learning curve

This section is intended to show reasoning and its correction, not just
results. All items are drawn from `AUDIT.md` and the git history.

### 10.1 The error that mattered most

**The headline finding was produced by a bug, and the bug made the result look
better than the data supported.**

`scripts/fase3_regressie.py` called the walk-forward routine as
`walk_forward_validate(target, drivers, min_train=1000, step=21)` — omitting
`horizon`, which then defaulted to 1. The procedure predicted one day, skipped
twenty, and repeated: **145 disjoint days** separated by three-week gaps,
rather than 3,024 continuous ones.

| Configuration | n | OOS R² | Accuracy | vs random walk |
|---|---|---|---|---|
| `horizon=1, step=21` (published for months) | 145 | −0.0396 | 43.8% | +1.96% |
| `horizon=21, step=21` (correct) | 3,024 | +0.0110 | 51.9% | −0.55% |

The sign of the headline result reversed. The published claim — *"directional
accuracy 43.8%, worse than a coin flip"* — was noise on a scattered subsample.

**The conclusion survived; the evidence did not.** Direction remains
unpredictable, but because the corrected edge is insignificant (p = 0.170), not
because the model underperforms chance. The old numbers **overstated** the
negative result, which is in a sense worse than overstating a positive one: the
paper would have asserted something stronger than the data allowed.

Three reasons it went unnoticed for so long, each generalisable:

1. **Nothing crashed.** The function did exactly what it was asked to do.
2. **The number matched the expectation.** An R² of −0.04 fitted the narrative
   being told. Surprising numbers in this project were checked carefully; the
   one that confirmed the story was waved through. *A result that matches your
   hypothesis deserves more scrutiny, not less.*
3. **It reproduced perfectly.** Every run returned −0.0396, which was treated
   as confirmation. But **reproducibility is not correctness** — a script that
   deterministically reproduces its own bug passes the first test and fails the
   second.

It surfaced only because `scripts/freeze_results.py` was written as an
independent implementation and disagreed. *Two implementations that disagree
find errors that one implementation cannot find by running a hundred times.*

A sharper detail: this exact bug was already described in the project's own
walkthrough document as a mistake that had been *found and fixed*. It was fixed
in `pipeline.py` and never in the script that generated the published numbers.
**Documenting a fix is not applying one.** The guard now lives in the code —
`walk_forward_validate` raises on `horizon < step` unless `allow_gaps=True` is
passed explicitly — with three tests enforcing it, including one asserting that
the default parameters produce a continuous series.

### 10.2 Compounding log returns as simple returns

`backtest.py` computed equity curves as $(1+r)\prod$ while the inputs were log
returns. Correct is $\exp(\sum r)$.

| Quantity | As coded | Correct | Actual price move |
|---|---|---|---|
| Gold total return | 714.3% | **1,114.2%** | 1,114.2% |
| Max drawdown | −48.37% | **−44.36%** | — |

Scope matters here and was verified rather than assumed: `annual_return`,
`annual_volatility` and every **Sharpe ratio were unaffected**, since they
derive from the mean and standard deviation of the daily series and never touch
the equity curve. Only `total_return`, `max_drawdown` and `equity_curve` were
wrong. A regression test now pins both the fix and its scope.

### 10.3 Earlier errors, corrected during development

| Error | Consequence | Correction |
|---|---|---|
| Spectral analysis used a white-noise permutation null | "Found" a 1,483-day cycle; 111/590 frequencies significant | AR(1) null preserving persistence → 53/590, peak explains 0.8% |
| Sine-wave model validated at a 540-day horizon | "Beat" naive by 28% | Tied *exactly* with a constant-only control, proving the wave contributed nothing; at a 21-day horizon it was 66% worse |
| Margin calculation summed all deposits | Overstated loss ($17,073 vs $13,640) | Peak *net* outlay; quarterly buffer fell 30.3% → 24.8% |
| Coverage percentages estimated, not measured | Claimed 80%/90% | Measured 68.1%/86.1% |
| Claimed Kupiec rejected GBM-normal (p = 0.045) | A false finding | The p-value flipped with the random seed; at 3,000 paths p = 0.101. It was Monte Carlo noise in my own simulation |
| Assumed volatility clustering always inflates HAC errors | Wrong mechanism | Only when driver *and* error are autocorrelated (0.95 vs 2.21) |
| Claimed adjusted R² penalises useless variables | Overconfident | 200 noise columns raised plain R² from 0.186 to 0.219, and adjusted R² *also* rose up to ~50 columns |
| Claimed core series are never revised | Factually wrong | ALFRED shows DTWEXBGS had 249/261 observations revised (mean 1.36%) |
| Roll effects asserted "small for gold" | Unverified assertion | Now measured: p = 0.728 (mean), 0.219 (variance). The assertion held, but it was an assumption until tested |

### 10.4 How the approach evolved

The project began as a prediction exercise: regress gold returns on macro
drivers, find the relationship, trade it. The in-sample R² of 0.187 looked
encouraging. Walk-forward validation reduced that to 0.011, insignificant.

Rather than tuning until something worked, the question was reframed: **if
direction is unpredictable but magnitude is not, what useful question does the
predictable part answer?** That led to margin sizing, which needs only a
volatility forecast.

Three further reframings followed, each forced by evidence:

1. The failed strategy was **kept in** rather than deleted, because it is the
   evidence for the first half of the claim and because the cost analysis
   (gross −0.001 → net −0.163) is a result in its own right.
2. When the GARCH buffer lost to a fixed 25% rule, that was **reported as the
   conclusion** rather than tuned away. Adjusting parameters until the
   preferred model wins measures the researcher's degrees of freedom, not the
   model.
3. When the audit established that "hedge" was asserted but never modelled, the
   hedge question was **tested directly** (§6.4) rather than quietly dropped,
   producing an independent negative result.

### 10.5 What I would do differently

1. **Write the validation harness before the model.** Every substantive error
   was caught by validation, and the two largest were caught by an
   *independent* implementation. That should have been the starting point.
2. **Freeze the end date on day one.** Floating end dates made results
   irreproducible and masked the conditional-buffer finding for months.
   `ANALYSIS_END_DATE` now enforces it.
3. **Put guards in code, not prose.** The horizon bug was documented as fixed
   and persisted anyway.
4. **Treat expectation-confirming results as suspect.** The single most costly
   error survived because it agreed with the hypothesis.
5. **Define the hedged exposure before modelling the hedge.** Several months of
   margin work rests on an offset that was never quantified.
6. **Report conditional quantities conditionally.** A number like "the 99%
   buffer" implied an unconditional constant that does not exist.

---

## 11. Further work

Ordered by expected value relative to effort.

1. **Measure basis risk** between physical gold and front-month futures, using
   spot or multi-contract data. This is the missing piece that would make the
   margin analysis genuinely about hedging.
2. **Condition the buffer explicitly on starting volatility** and publish it as
   a function or lookup table rather than a scalar, following §7.1.
3. **Compare against asymmetric volatility models** (EGARCH, GJR-GARCH). Gold's
   leverage effect may differ in sign from equities, which is interesting in
   itself.
4. **Extend the coverage test using overlapping windows with a block bootstrap**
   to recover statistical power without pretending independence.
5. **Run the walk-forward on true point-in-time data** via ALFRED. The
   machinery is built and tested; only the pipeline wiring remains.
6. **Test cointegration between gold and real rates in levels**, which the
   current differencing discards.
7. **Extend to a crack-spread / refined-products application**, already drafted
   in the project backlog.

---

## 12. References

Only sources actually used in the code or documentation. Items marked
**[VERIFY]** need their bibliographic details confirmed before citation — the
method is used and correctly described, but the exact reference was not
checked.

**Data sources (verified, these are the actual endpoints used):**

- Federal Reserve Bank of St. Louis, FRED database. Series: `DFII10`,
  `DTWEXBGS`, `T10YIE`, `T10Y2Y`, `DFF`, `WALCL`, `BAMLH0A0HYM2`.
  https://fred.stlouisfed.org
- Federal Reserve Bank of St. Louis, ALFRED archival database (vintage data).
  https://alfred.stlouisfed.org
- Yahoo Finance via the `yfinance` Python package. Tickers: `GC=F`, `SI=F`,
  `^VIX`, `^GSPC`, `DX-Y.NYB`.

**Methods:**

- Bollerslev, T. (1986). "Generalized Autoregressive Conditional
  Heteroskedasticity." *Journal of Econometrics*, 31(3), 307–327. **[VERIFY]**
- Newey, W. K., & West, K. D. (1987). "A Simple, Positive Semi-Definite,
  Heteroskedasticity and Autocorrelation Consistent Covariance Matrix."
  *Econometrica*, 55(3), 703–708. **[VERIFY]**
- Kupiec, P. (1995). "Techniques for Verifying the Accuracy of Risk Measurement
  Models." *Journal of Derivatives*, 3(2), 73–84. **[VERIFY]**
- Christoffersen, P. F. (1998). "Evaluating Interval Forecasts."
  *International Economic Review*, 39(4), 841–862. **[VERIFY]**
- Diebold, F. X., & Mariano, R. S. (1995). "Comparing Predictive Accuracy."
  *Journal of Business & Economic Statistics*, 13(3), 253–263. **[VERIFY]**
- Ederington, L. H. (1979). "The Hedging Performance of the New Futures
  Markets." *Journal of Finance*, 34(1), 157–170. **[VERIFY]**
- Dickey, D. A., & Fuller, W. A. (1979). "Distribution of the Estimators for
  Autoregressive Time Series with a Unit Root." *JASA*, 74(366), 427–431.
  **[VERIFY]**
- Kwiatkowski, D., Phillips, P. C. B., Schmidt, P., & Shin, Y. (1992).
  "Testing the Null Hypothesis of Stationarity against the Alternative of a
  Unit Root." *Journal of Econometrics*, 54(1–3), 159–178. **[VERIFY]**
- J.P. Morgan / Reuters (1996). *RiskMetrics Technical Document*, 4th edition.
  Source of the EWMA λ = 0.94 benchmark. **[VERIFY]**

**Software (versions verified from the frozen run manifest):**

- Python 3.12.10; `numpy` 2.5.3, `pandas` 3.0.5, `scipy` 1.18.1,
  `statsmodels` 0.15.0, `arch` 8.0.0.

**Not cited because not used:** no textbook, blog post or secondary source
informed the specifications. The margin mechanics follow standard CME contract
specifications (100 troy oz per COMEX gold contract, ~5% initial margin), which
should be cited from CME's own documentation if the paper states them. **[VERIFY]**

---

## 13. Appendix: reproduction

### Commit

```
Code and results:  fd47945
Results generated at: e060126ffe3cb8eeb59c8b458d180a5fd4c429a8
Branch: main
```

The frozen outputs in `results/` were generated at commit `e060126` and
committed in `e375c87`/`fd47945`. The code is byte-identical across those
commits (only `results/` differs), so the outputs reproduce from any of them.

### Environment

```
Python   3.12.10
Platform Windows-11-10.0.26200-SP0
numpy       2.5.3
pandas      3.0.5
scipy       1.18.1
statsmodels 0.15.0
arch        8.0.0
```

Requires a free FRED API key in a `.env` file as `FRED_API_KEY` (gitignored).

### Commands

```bash
# 1. Fetch data (writes a local parquet cache)
python scripts/fetch_data.py

# 2. Reproduce the frozen results: all numbers, figures and tables
python scripts/analyse_hedge.py --json results/hedge_numbers.json
python scripts/meet_datadrift.py --json results/drift_numbers.json
python scripts/freeze_results.py

# 3. Individual analysis stages
python scripts/fase2_stationariteit.py   # ADF / KPSS
python scripts/fase2_correlaties.py      # correlations, stability
python scripts/fase3_regressie.py        # OLS/NW, walk-forward
python scripts/fase4_simulatie.py        # Monte Carlo, VaR/ES
python scripts/valideer_buffer.py        # coverage vs benchmarks
python scripts/pipeline.py               # end-to-end + run manifest

# 4. Tests
python -m pytest tests/ -q               # 196 tests
```

### Output files

| File | Contents |
|---|---|
| `results/key_numbers.json` | 120 numbers, each with value, unit, sample period, frequency and producing function |
| `results/tables/walk_forward_metrics.csv` | out-of-sample metrics by model |
| `results/tables/coverage_comparison.csv` | Kupiec / Christoffersen vs three benchmarks |
| `results/tables/df_sensitivity.csv` | buffer vs degrees of freedom |
| `results/tables/buffer_conditional_on_start_state.csv` | buffer vs starting volatility |
| `results/figures/fig1…fig6.pdf` (+ `.png`) | six vector figures |

Determinism: seed 42 throughout; 20,000 paths for headline simulations,
100,000 for the sensitivity sweep (where 2,000 proved noise-dominated).
`results/key_numbers.json` carries a `_manifest` block with the commit hash,
end date, seed, path count and package versions.

### Important note for the paper's numbers

`results/key_numbers.json` stores fractions, not percentages:
`buffer_99_garch_t = 0.3696` means 36.96% of notional. Correlations, R² and
p-values are dimensionless. The `source` field on each entry names the function
that produced it, so any figure in the paper can be traced to code.
