"""Bevriest alle kerngetallen, figuren en tabellen in results/.

Waarom dit bestaat
------------------
Een paper moet na te rekenen zijn. Dat betekent: elk getal in de tekst hoort
terug te voeren op een bestand met een vaste waarde, niet op een berekening
die morgen iets anders oplevert.

Dit script draait alles één keer op de bevroren einddatum en schrijft:

    results/key_numbers.json    elk getal met eenheid, periode en herkomst
    results/figures/*.pdf,*.png vectorfiguren voor LaTeX
    results/tables/*.csv        tabellen

Elk getal krijgt vijf velden mee: value, unit, sample_period, frequency en
source - dat laatste is het bestand en de functie die het produceerde.

Gebruik:
    python scripts/freeze_results.py
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.backtest import CostModel, run_backtest, sharpe_significance  # noqa: E402
from goldmodel.config import ALL_SERIES, ANALYSIS_END_DATE  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.models import walk_forward_validate  # noqa: E402
from goldmodel.placebo import effective_sample_size  # noqa: E402
from goldmodel.signal import (  # noqa: E402
    SignalSettings,
    position_statistics,
    predictions_to_positions,
)
from goldmodel.simulate import (  # noqa: E402
    GarchParameters,
    SimulationSettings,
    fit_garch,
    simulate_garch,
    simulate_gbm_normal,
)
from goldmodel.validation import (  # noqa: E402
    compare_buffer_rules,
    ewma_buffer,
    fixed_buffer,
    rolling_percentile_buffer,
)
from goldmodel.viz.correlations import build_change_panel  # noqa: E402

RESULTS = PROJECT_ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"

DRIVERS = ["real_rate_10y", "usd_broad_index", "breakeven_inflation_10y", "vix"]
HORIZON_DAYS = 63
SEED = 42
N_PATHS = 20_000

SAMPLE = f"2003-01-02 tot {ANALYSIS_END_DATE}"

numbers: dict = {}


def record(
    name: str,
    value: float | int | str,
    *,
    unit: str,
    source: str,
    sample: str = SAMPLE,
    frequency: str = "dagelijks",
    note: str = "",
) -> None:
    """Legt één getal vast met zijn herkomst."""
    numbers[name] = {
        "value": value,
        "unit": unit,
        "sample_period": sample,
        "frequency": frequency,
        "source": source,
    }
    if note:
        numbers[name]["note"] = note


def save_figure(fig: plt.Figure, stem: str) -> None:
    """Schrijft een figuur als vector-PDF en PNG."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    {stem}.pdf + .png")


def main() -> int:
    """Draait alles en bevriest de uitkomsten."""
    warnings.simplefilter("ignore")
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "legend.fontsize": 10,
            "figure.dpi": 100,
        }
    )
    RESULTS.mkdir(exist_ok=True)
    TABLES.mkdir(exist_ok=True)

    print("=" * 78)
    print(f"RESULTATEN BEVRIEZEN  (einddatum {ANALYSIS_END_DATE})")
    print("=" * 78)

    # -- data -------------------------------------------------------------
    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    changes = build_change_panel(panel)

    prices = panel["gold_futures"].dropna()
    gold = changes["gold_futures"].dropna()

    print("\n[1/6] Data en verdeling")
    record(
        "n_trading_days", len(gold), unit="dagen", source="DataLoader.build_panel"
    )
    record(
        "gold_price_final",
        round(float(prices.iloc[-1]), 2),
        unit="USD per troy ounce",
        source="panel['gold_futures']",
    )
    record(
        "gold_price_first",
        round(float(prices.iloc[0]), 2),
        unit="USD per troy ounce",
        source="panel['gold_futures']",
    )
    record(
        "gold_total_return",
        round(float(prices.iloc[-1] / prices.iloc[0] - 1), 4),
        unit="fractie",
        source="panel['gold_futures']",
    )
    record(
        "annualised_volatility",
        round(float(gold.std() * np.sqrt(252)), 4),
        unit="fractie per jaar",
        source="changes['gold_futures'].std() * sqrt(252)",
    )
    record(
        "kurtosis_excess",
        round(float(sps.kurtosis(gold, fisher=True)), 3),
        unit="dimensieloos",
        source="scipy.stats.kurtosis(fisher=True)",
        note="excess kurtosis; normaal = 0",
    )
    record(
        "skewness",
        round(float(sps.skew(gold)), 3),
        unit="dimensieloos",
        source="scipy.stats.skew",
    )
    jb_stat, jb_p = sps.jarque_bera(gold)
    record(
        "jarque_bera_p",
        float(f"{jb_p:.3e}"),
        unit="p-waarde",
        source="scipy.stats.jarque_bera",
        note="H0 = normaliteit",
    )
    beyond_3sigma = int((gold.abs() > 3 * gold.std()).sum())
    record(
        "days_beyond_3sigma",
        beyond_3sigma,
        unit="dagen",
        source="(|r| > 3*sigma).sum()",
    )
    record(
        "days_beyond_3sigma_normal_expectation",
        round(float(len(gold) * 2 * (1 - sps.norm.cdf(3))), 1),
        unit="dagen",
        source="len(r) * 2 * (1 - Phi(3))",
    )

    # -- fase 3: voorspelbaarheid -----------------------------------------
    print("[2/6] Walk-forward validatie")
    available = [d for d in DRIVERS if d in changes.columns]
    walk_forward = walk_forward_validate(
        gold, changes[available], min_train=1000, horizon=21, step=21
    )
    metrics = walk_forward.metrics
    metrics.to_csv(TABLES / "walk_forward_metrics.csv")
    print("    walk_forward_metrics.csv")

    for model in ("ols", "random_walk", "historisch"):
        if model not in metrics.index:
            continue
        row = metrics.loc[model]
        suffix = model
        record(
            f"oos_r2_{suffix}",
            round(float(row["r2_oos"]), 4),
            unit="dimensieloos",
            source="models.walk_forward_validate",
            frequency="21-daagse vensters",
        )
        if isinstance(row["directional_accuracy"], (int, float)):
            record(
                f"directional_accuracy_{suffix}",
                round(float(row["directional_accuracy"]), 4),
                unit="fractie",
                source="models.walk_forward_validate",
                frequency="21-daagse vensters",
            )
    record(
        "rmse_vs_random_walk_ols",
        round(float(metrics.loc["ols", "rmse_vs_benchmark_pct"]), 3),
        unit="procent (positief = slechter)",
        source="models.walk_forward_validate",
    )
    record(
        "n_oos_days",
        int(len(walk_forward.actuals)),
        unit="dagen",
        source="models.walk_forward_validate",
    )
    record(
        "n_folds",
        int(walk_forward.n_folds),
        unit="vensters",
        source="models.walk_forward_validate",
    )

    # -- backtest ---------------------------------------------------------
    print("[3/6] Backtest met kosten")
    predictions = walk_forward.predictions["ols"]
    positions = predictions_to_positions(
        predictions, SignalSettings(method="linear", max_position=1.0)
    )
    statistics = position_statistics(positions)
    backtest = run_backtest(
        positions, gold, cost_model=CostModel(), execution_lag=1
    )
    gross, net = backtest.metrics["gross"], backtest.metrics["net"]

    record(
        "annual_turnover",
        round(float(statistics["annual_turnover"]), 1),
        unit="omzet per jaar",
        source="signal.position_statistics",
    )
    record(
        "sign_flip_share",
        round(
            float(
                (np.sign(positions).diff().abs() > 0).sum() / len(positions)
            ),
            4,
        ),
        unit="fractie van de dagen",
        source="signal.predictions_to_positions",
    )
    record(
        "position_autocorrelation_lag1",
        round(float(positions.autocorr(1)), 4),
        unit="dimensieloos",
        source="positions.autocorr(1)",
    )
    for label, block in (("gross", gross), ("net", net)):
        record(
            f"sharpe_{label}",
            round(float(block["sharpe"]), 4),
            unit="dimensieloos",
            source="backtest._performance_metrics",
        )
        record(
            f"annual_return_{label}",
            round(float(block["annual_return"]), 5),
            unit="fractie per jaar",
            source="backtest._performance_metrics",
        )
        record(
            f"max_drawdown_{label}",
            round(float(block["max_drawdown"]), 4),
            unit="fractie",
            source="backtest._performance_metrics",
            note="na correctie: exp(cumsum), niet (1+r).cumprod()",
        )
    record(
        "sharpe_standard_error",
        round(float(net["sharpe_standard_error"]), 4),
        unit="dimensieloos",
        source="backtest._performance_metrics",
        note="1/sqrt(jaren)",
    )
    significance = sharpe_significance(backtest.net_returns)
    # De drempel waarboven een Sharpe van nul te onderscheiden is: 1,96 keer
    # de standaardfout. Die standaardfout is 1/sqrt(jaren), dus met twaalf
    # jaar data heb je al 0,57 nodig voordat je uberhaupt iets mag beweren.
    record(
        "sharpe_required_for_significance",
        round(1.96 * float(significance["standard_error"]), 3),
        unit="dimensieloos",
        source="1.96 * backtest.sharpe_significance()['standard_error']",
        note="drempel op 5% tweezijdig",
    )
    record(
        "sharpe_t_statistic_net",
        round(float(significance["t_statistic"]), 3),
        unit="dimensieloos",
        source="backtest.sharpe_significance",
    )
    record(
        "sharpe_significant_net",
        str(significance["significant"]),
        unit="waar/onwaar",
        source="backtest.sharpe_significance",
        note="|t| > 1,96",
    )

    # -- fase 4: simulatie en buffer --------------------------------------
    print("[4/6] Monte Carlo en margebuffer")
    garch = fit_garch(gold)
    record(
        "garch_alpha",
        round(float(garch.alpha), 5),
        unit="dimensieloos",
        source="simulate.fit_garch",
    )
    record(
        "garch_beta",
        round(float(garch.beta), 5),
        unit="dimensieloos",
        source="simulate.fit_garch",
    )
    record(
        "garch_persistence",
        round(float(garch.alpha + garch.beta), 5),
        unit="dimensieloos",
        source="simulate.fit_garch",
        note="alpha + beta",
    )
    record(
        "garch_half_life",
        round(float(np.log(0.5) / np.log(garch.alpha + garch.beta)), 1),
        unit="handelsdagen",
        source="log(0.5)/log(alpha+beta)",
    )
    record(
        "garch_df",
        round(float(garch.degrees_of_freedom), 3),
        unit="vrijheidsgraden",
        source="simulate.fit_garch (MLE)",
    )
    record(
        "garch_df_se",
        round(float(garch.degrees_of_freedom_se), 3),
        unit="standaardfout",
        source="arch std_err['nu']",
    )
    record(
        "garch_start_volatility",
        round(float(np.sqrt(garch.last_variance * 252)), 4),
        unit="fractie per jaar",
        source="sqrt(last_variance * 252)",
        note="conditionele volatiliteit op de laatste dag",
    )
    record(
        "garch_long_run_volatility",
        round(float(np.sqrt(garch.long_run_variance * 252)), 4),
        unit="fractie per jaar",
        source="sqrt(long_run_variance * 252)",
    )

    settings = SimulationSettings(
        n_paths=N_PATHS, horizon_days=HORIZON_DAYS, seed=SEED, is_short=True
    )
    garch_simulation = simulate_garch(float(gold.mean()), garch, settings)
    gbm_simulation = simulate_gbm_normal(
        float(gold.mean()), float(gold.std()), settings
    )

    record(
        "buffer_99_garch_t",
        round(float(garch_simulation.value_at_risk(0.99)), 4),
        unit="fractie van notioneel",
        source="simulate.simulate_garch",
        frequency="63-daagse horizon",
        note=(
            f"seed {SEED}, {N_PATHS} paden. CONDITIONEEL op een "
            f"startvolatiliteit van "
            f"{np.sqrt(garch.last_variance * 252) * 100:.1f}% op "
            f"{ANALYSIS_END_DATE}. Zonder die toestand is het getal niet te "
            f"interpreteren - zie buffer_conditional_table."
        ),
    )

    # De buffer is een CONDITIONELE grootheid. Eén kopgetal rapporteren
    # suggereert een precisie die er niet is: dezelfde code gaf 25% tot 66%
    # over zes einddatums, puur doordat de startvolatiliteit verschilde.
    #
    # Deze tabel houdt de steekproef en alle parameters VAST en varieert
    # alleen de startvariantie. Dat isoleert het effect.
    conditional_rows = []
    for ratio in (0.5, 0.67, 1.0, 1.17, 1.79, 3.16, 4.0):
        variant = GarchParameters(
            omega=garch.omega,
            alpha=garch.alpha,
            beta=garch.beta,
            degrees_of_freedom=garch.degrees_of_freedom,
            last_variance=garch.long_run_variance * ratio,
            long_run_variance=garch.long_run_variance,
        )
        outcome = simulate_garch(float(gold.mean()), variant, settings)
        conditional_rows.append(
            {
                "vol_ratio": ratio,
                "start_vol_pct": round(
                    float(np.sqrt(variant.last_variance * 252) * 100), 1
                ),
                "buffer_99_pct": round(outcome.value_at_risk(0.99) * 100, 1),
                "es_99_pct": round(outcome.expected_shortfall(0.99) * 100, 1),
            }
        )
    conditional = pd.DataFrame(conditional_rows)
    conditional.to_csv(TABLES / "buffer_conditional_on_start_state.csv", index=False)
    print("    buffer_conditional_on_start_state.csv")

    record(
        "buffer_99_range_low",
        round(float(conditional["buffer_99_pct"].min() / 100), 4),
        unit="fractie van notioneel",
        source="scripts/freeze_results.py startvariantie-sweep",
        frequency="63-daagse horizon",
        note=f"bij een startvolatiliteit van {conditional['start_vol_pct'].min():.1f}%",
    )
    record(
        "buffer_99_range_high",
        round(float(conditional["buffer_99_pct"].max() / 100), 4),
        unit="fractie van notioneel",
        source="scripts/freeze_results.py startvariantie-sweep",
        frequency="63-daagse horizon",
        note=f"bij een startvolatiliteit van {conditional['start_vol_pct'].max():.1f}%",
    )
    record(
        "buffer_99_at_long_run_vol",
        round(
            float(
                conditional.loc[
                    conditional["vol_ratio"] == 1.0, "buffer_99_pct"
                ].iloc[0]
                / 100
            ),
            4,
        ),
        unit="fractie van notioneel",
        source="scripts/freeze_results.py startvariantie-sweep",
        frequency="63-daagse horizon",
        note="startvolatiliteit gelijk aan het langetermijngemiddelde",
    )
    record(
        "es_99_garch_t",
        round(float(garch_simulation.expected_shortfall(0.99)), 4),
        unit="fractie van notioneel",
        source="simulate.simulate_garch",
        frequency="63-daagse horizon",
    )
    record(
        "buffer_99_gbm_normal",
        round(float(gbm_simulation.value_at_risk(0.99)), 4),
        unit="fractie van notioneel",
        source="simulate.simulate_gbm",
        frequency="63-daagse horizon",
    )
    for rule_pct in (0.05, 0.10):
        covered = float((garch_simulation.max_adverse <= rule_pct).mean())
        record(
            f"coverage_of_{int(rule_pct * 100)}pct_rule",
            round(covered, 4),
            unit="fractie van de paden",
            source="simulate.simulate_garch",
            frequency="63-daagse horizon",
        )

    # df-gevoeligheid
    sensitivity_rows = []
    for df in (3.0, 3.5, 4.0, 4.21, 5.0, 5.39, 6.0, 8.0):
        variant = GarchParameters(
            omega=garch.omega,
            alpha=garch.alpha,
            beta=garch.beta,
            degrees_of_freedom=df,
            last_variance=garch.last_variance,
            long_run_variance=garch.long_run_variance,
        )
        outcome = simulate_garch(
            float(gold.mean()),
            variant,
            SimulationSettings(
                n_paths=100_000, horizon_days=HORIZON_DAYS, seed=SEED, is_short=True
            ),
        )
        sensitivity_rows.append(
            {
                "df": df,
                "buffer_99_pct": round(outcome.value_at_risk(0.99) * 100, 1),
                "es_99_pct": round(outcome.expected_shortfall(0.99) * 100, 1),
            }
        )
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(TABLES / "df_sensitivity.csv", index=False)
    print("    df_sensitivity.csv")
    record(
        "df_sensitivity_spread_full_range",
        round(
            float(
                sensitivity["buffer_99_pct"].max()
                - sensitivity["buffer_99_pct"].min()
            ),
            1,
        ),
        unit="procentpunt",
        source="scripts/freeze_results.py df-sweep",
        note="df van 3 tot 8, 100k paden, common random numbers",
    )

    # -- dekkingstoets ----------------------------------------------------
    print("[5/6] Dekkingstoets tegen vuistregels")
    values = gold.dropna()
    starts = pd.Index(
        [
            values.index[p]
            for p in range(1000, len(values) - HORIZON_DAYS, HORIZON_DAYS)
        ]
    )
    realised = {}
    for start in starts:
        position = values.index.get_loc(start)
        window = values.iloc[position : position + HORIZON_DAYS].to_numpy()
        if len(window) < HORIZON_DAYS:
            continue
        path = np.concatenate([[0.0], np.cumsum(window)])
        realised[start] = float(np.expm1(path.max()))
    realised_series = pd.Series(realised).sort_index()

    garch_buffers = {}
    for index, start in enumerate(starts):
        history = values.loc[values.index < start]
        if len(history) < 500:
            continue
        try:
            parameters = fit_garch(history)
            outcome = simulate_garch(
                float(history.mean()),
                parameters,
                SimulationSettings(
                    n_paths=2000,
                    horizon_days=HORIZON_DAYS,
                    seed=SEED + index,
                    is_short=True,
                ),
            )
            garch_buffers[start] = outcome.value_at_risk(0.99)
        except Exception:  # noqa: BLE001
            continue

    rules = {
        "garch_t": pd.Series(garch_buffers).sort_index(),
        "vast_25pct": fixed_buffer(starts, level=0.25),
        "rolling_p99": rolling_percentile_buffer(
            gold, starts, horizon_days=HORIZON_DAYS
        ),
        "ewma_094": ewma_buffer(gold, starts, horizon_days=HORIZON_DAYS),
    }
    coverage_table, coverage_results = compare_buffer_rules(
        rules, realised_series, confidence=0.99
    )
    coverage_table.to_csv(TABLES / "coverage_comparison.csv", index=False)
    print("    coverage_comparison.csv")

    first = next(iter(coverage_results.values()))
    record(
        "n_quarters_tested",
        int(first.n_periods),
        unit="niet-overlappende kwartalen",
        source="validation.compare_buffer_rules",
        frequency="kwartaal",
        note="94 passen er rekenkundig in; 78 resteren na 1000 dagen burn-in",
    )
    record(
        "expected_breaches_at_99pct",
        round(float(first.expected_breaches), 3),
        unit="aantal",
        source="validation.evaluate_coverage",
        frequency="kwartaal",
        note="hieronder is elke toets onderbemeten",
    )
    for label, result in coverage_results.items():
        record(
            f"breaches_{label}",
            int(result.n_breaches),
            unit="aantal",
            source="validation.evaluate_coverage",
            frequency="kwartaal",
        )
        record(
            f"kupiec_p_{label}",
            round(float(result.kupiec_p), 4),
            unit="p-waarde",
            source="validation.kupiec_pof_test",
            frequency="kwartaal",
        )
        record(
            f"mean_buffer_{label}",
            round(float(result.mean_buffer), 4),
            unit="fractie van notioneel",
            source="validation.evaluate_coverage",
            frequency="kwartaal",
        )

    # effectieve steekproef
    realised_vol = gold.rolling(21).std().dropna()
    ess = effective_sample_size(realised_vol)
    record(
        "effective_sample_size_volatility",
        int(ess["n_effective"]),
        unit="waarnemingen",
        source="placebo.effective_sample_size",
        note="na correctie voor autocorrelatie in 21-daagse realised vol",
    )

    # -- figuren ----------------------------------------------------------
    print("[6/6] Figuren")

    # F1: verdeling met normaal ernaast
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.hist(
        gold * 100, bins=120, density=True, alpha=0.65,
        color="#4C72B0", label=f"goud (n={len(gold):,})",
    )
    grid = np.linspace(gold.min() * 100, gold.max() * 100, 400)
    ax.plot(
        grid,
        sps.norm.pdf(grid, gold.mean() * 100, gold.std() * 100),
        "r--", lw=1.8, label="normaal, zelfde gem./std",
    )
    ax.set_xlabel("dagelijks log-rendement (%)")
    ax.set_ylabel("dichtheid")
    ax.set_title(
        f"Dikke staarten: excess kurtosis "
        f"{numbers['kurtosis_excess']['value']}"
    )
    ax.legend(frameon=False)
    ax.set_xlim(-6, 6)
    save_figure(fig, "fig1_return_distribution")

    # F2: volatiliteitsclustering
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    rolling = gold.rolling(63).std() * np.sqrt(252) * 100
    ax.plot(rolling.index, rolling.to_numpy(), lw=0.9, color="#C44E52")
    ax.axhline(
        float(gold.std() * np.sqrt(252) * 100), ls="--", lw=1,
        color="grey", label="gemiddelde over de hele reeks",
    )
    ax.set_xlabel("jaar")
    ax.set_ylabel("volatiliteit (% per jaar)")
    ax.set_title(
        f"Volatiliteitsclustering: persistentie "
        f"{numbers['garch_persistence']['value']}, "
        f"halfwaardetijd {numbers['garch_half_life']['value']:.0f} dagen"
    )
    ax.legend(frameon=False)
    save_figure(fig, "fig2_volatility_clustering")

    # F3: out-of-sample voorspelkracht
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    order = ["random_walk", "historisch", "ols", "ridge"]
    present = [m for m in order if m in metrics.index]
    heights = [float(metrics.loc[m, "r2_oos"]) for m in present]
    colours = ["grey" if h >= 0 else "#C44E52" for h in heights]
    ax.bar(present, heights, color=colours)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("out-of-sample $R^2$")
    ax.set_xlabel("model")
    ax.set_title(
        f"Richting is niet voorspelbaar (n={numbers['n_oos_days']['value']:,} dagen)"
    )
    for position, height in enumerate(heights):
        ax.text(
            position, height + (0.004 if height >= 0 else -0.004),
            f"{height:+.4f}", ha="center",
            va="bottom" if height >= 0 else "top", fontsize=9,
        )
    save_figure(fig, "fig3_oos_r2")

    # F4: buffer tegen vuistregel
    fig, ax = plt.subplots(figsize=(6.5, 4))
    excursions = np.sort(garch_simulation.max_adverse) * 100
    cumulative = np.arange(1, len(excursions) + 1) / len(excursions) * 100
    ax.plot(excursions, cumulative, lw=1.6, color="#4C72B0")
    for rule, colour in ((5, "#C44E52"), (10, "#DD8452")):
        covered = numbers[f"coverage_of_{rule}pct_rule"]["value"] * 100
        ax.axvline(rule, ls="--", lw=1.2, color=colour)
        ax.text(
            rule + 0.6, 30, f"{rule}%-regel\ndekt {covered:.0f}%",
            fontsize=9, color=colour,
        )
    buffer_99 = numbers["buffer_99_garch_t"]["value"] * 100
    ax.axhline(99, ls=":", lw=1, color="grey")
    ax.axvline(buffer_99, ls="-", lw=1.4, color="green")
    ax.text(buffer_99 + 0.6, 60, f"99%-buffer\n{buffer_99:.1f}%", fontsize=9, color="green")
    ax.set_xlabel("maximale tegenbeweging over een kwartaal (%)")
    ax.set_ylabel("cumulatief percentage paden (%)")
    ax.set_title(f"Benodigde buffer tegen de vuistregel ({N_PATHS:,} paden)")
    ax.set_xlim(0, min(80, excursions.max()))
    save_figure(fig, "fig4_buffer_vs_rule_of_thumb")

    # F5: goud als hedge
    hedge_path = RESULTS / "hedge_numbers.json"
    if hedge_path.exists():
        hedge = json.loads(hedge_path.read_text(encoding="utf-8"))
        fig, ax = plt.subplots(figsize=(6.5, 3.8))
        labels = ["volledige\nsteekproef", "2008\nGFC", "maart\n2020", "2022\nbear"]
        keys = [
            "corr_gold_sp500",
            "corr_gold_sp500_stress_2008",
            "corr_gold_sp500_stress_maart",
            "corr_gold_sp500_stress_2022",
        ]
        values_list = [hedge.get(k, float("nan")) for k in keys]
        ax.bar(
            labels, values_list,
            color=["#4C72B0" if v < 0 else "#C44E52" for v in values_list],
        )
        ax.axhline(0, color="black", lw=0.9)
        ax.set_ylabel(r"correlatie met S&P 500")
        ax.set_title("Goud beschermt niet wanneer aandelen vallen")
        for position, value in enumerate(values_list):
            ax.text(
                position, value + (0.004 if value >= 0 else -0.004),
                f"{value:+.3f}", ha="center",
                va="bottom" if value >= 0 else "top", fontsize=9,
            )
        save_figure(fig, "fig5_gold_not_an_equity_hedge")

    # F6: de buffer hangt aan de starttoestand.
    #
    # Twee reeksen in één figuur, en dat is bewust:
    #   - de gecontroleerde sweep (vaste steekproef, alleen startvariantie)
    #     is het BEWIJS van het mechanisme;
    #   - de zes einddatums zijn hoe het ONTDEKT werd.
    # De tweede alleen zou zwak zijn (N=6, één invloedrijk punt); de eerste
    # alleen zou verbergen dat het een praktisch probleem is.
    drift_path = RESULTS / "drift_numbers.json"
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(
        conditional["start_vol_pct"], conditional["buffer_99_pct"],
        "o-", lw=1.6, color="#4C72B0", zorder=3,
        label="gecontroleerd: vaste steekproef, alleen startvol varieert",
    )
    correlation = float("nan")
    if drift_path.exists():
        drift = json.loads(drift_path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(drift["rows"])
        ax.scatter(
            frame["startvol_pct"], frame["buffer_99_pct"],
            s=85, marker="s", color="#C44E52", zorder=4,
            label="waargenomen: zes einddatums, zelfde code",
        )
        for _, row in frame.iterrows():
            ax.annotate(
                row["einddatum"],
                (row["startvol_pct"], row["buffer_99_pct"]),
                textcoords="offset points", xytext=(8, -4), fontsize=7.5,
            )
        correlation = float(
            np.corrcoef(frame["vol_ratio"], frame["buffer_99_pct"])[0, 1]
        )
    ax.set_xlabel("geannualiseerde volatiliteit op de startdatum (%)")
    ax.set_ylabel("99%-buffer (% van notioneel)")
    ax.set_title("De buffer is conditioneel op de starttoestand")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save_figure(fig, "fig6_buffer_depends_on_start_state")

    if drift_path.exists():
        record(
            "buffer_spread_across_end_dates",
            float(drift["buffer_spread_pp"]),
            unit="procentpunt",
            source="scripts/meet_datadrift.py",
            sample="einddatums 2025-09-30 tot 2026-10-13",
            frequency="kwartaal",
            note="zelfde code, alleen een andere einddatum",
        )
        record(
            "buffer_start_state_r_squared",
            round(correlation**2, 3),
            unit="dimensieloos",
            source="scripts/meet_datadrift.py",
            sample="6 einddatums",
            frequency="kwartaal",
            note="aandeel van de bufferspreiding verklaard door de startvolatiliteit",
        )

    # -- hedge-getallen overnemen -----------------------------------------
    if hedge_path.exists():
        hedge = json.loads(hedge_path.read_text(encoding="utf-8"))
        hedge_sample = f"{hedge['start_date']} tot {hedge['end_date']}"
        for key, value in hedge.items():
            if not isinstance(value, (int, float)):
                continue
            record(
                f"hedge_{key}",
                value,
                unit="zie naam",
                source="scripts/analyse_hedge.py",
                sample=hedge_sample,
            )

    # -- manifest ---------------------------------------------------------
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True,
            cwd=PROJECT_ROOT,
        ).stdout.strip()
    )

    payload = {
        "_manifest": {
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "analysis_end_date": ANALYSIS_END_DATE,
            "git_commit": commit,
            "git_dirty": dirty,
            "seed": SEED,
            "n_paths": N_PATHS,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {
                name: __import__(name).__version__
                for name in ("numpy", "pandas", "scipy", "statsmodels", "arch")
            },
        },
        "numbers": numbers,
    }
    (RESULTS / "key_numbers.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    print(f"\n  {len(numbers)} getallen -> results/key_numbers.json")
    print(f"  commit {commit[:12]}{' (DIRTY)' if dirty else ''}")
    print(f"  figuren: {len(list(FIGURES.glob('*.pdf')))} PDF")
    print(f"  tabellen: {len(list(TABLES.glob('*.csv')))} CSV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
