"""Tests voor de signaal- en backtestlaag.

De belangrijkste test in dit bestand is
``test_zero_lag_produces_impossible_returns``. Die bouwt een backtest MET
look-ahead bias en toont aan dat hij een absurd resultaat oplevert — en dat
de code zo'n backtest weigert te draaien.

Waarom dat de test is die telt: elke backtest kan mooie getallen produceren.
De vraag is of je opzet de meest voorkomende fout onmogelijk maakt. Deze test
legt vast dat hij dat doet, en laat zien hoe groot het verschil is.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.backtest import (  # noqa: E402
    CostModel,
    compare_to_benchmarks,
    placebo_backtest,
    run_backtest,
    sharpe_significance,
)
from goldmodel.signal import (  # noqa: E402
    SignalSettings,
    position_statistics,
    predictions_to_positions,
    turnover,
)


def make_index(n: int) -> pd.DatetimeIndex:
    """Werkdagenindex."""
    return pd.date_range("2010-01-01", periods=n, freq="B", name="date")


# -- DE LOOK-AHEAD TEST ---------------------------------------------------


def test_zero_lag_is_refused() -> None:
    """Een backtest zonder executie-lag wordt geweigerd.

    DE BELANGRIJKSTE TEST VAN DIT BESTAND.

    Een lag van nul betekent: handelen op de slotkoers van een dag die nog
    niet gesloten is. Dat is look-ahead bias, en het maakt elk resultaat
    waardeloos. De code moet dat onmogelijk maken, niet aan de gebruiker
    overlaten.
    """
    index = make_index(500)
    rng = np.random.default_rng(1)
    returns = pd.Series(rng.standard_normal(500) * 0.01, index=index)
    positions = pd.Series(1.0, index=index)

    with pytest.raises(ValueError, match="execution_lag moet minstens 1"):
        run_backtest(positions, returns, execution_lag=0)


def test_zero_lag_would_produce_impossible_returns() -> None:
    """Laat zien HOE GROOT de fout is die de lag voorkomt.

    We bouwen hier met de hand een backtest zonder lag — een perfect
    vooruitziend signaal — en vergelijken met dezelfde positie mét lag.

    Zonder lag is de Sharpe astronomisch, met lag is hij nul. Dat verschil
    is precies waarom de lag niet optioneel is.
    """
    index = make_index(1000)
    rng = np.random.default_rng(2)
    returns = pd.Series(rng.standard_normal(1000) * 0.01, index=index)

    # Een signaal dat het rendement van VANDAAG kent.
    cheating_positions = np.sign(returns)

    # Zonder lag: positie van dag t maal rendement van dag t.
    no_lag = (cheating_positions * returns).dropna()
    # Met lag: positie van dag t maal rendement van dag t+1.
    with_lag = run_backtest(cheating_positions, returns, execution_lag=1)

    no_lag_sharpe = float(
        no_lag.mean() / no_lag.std() * np.sqrt(252)
    )
    lagged_sharpe = float(with_lag.metrics["gross"]["sharpe"])

    # Zonder lag is elke dag winst: de "strategie" is nooit verkeerd.
    assert (no_lag > 0).mean() > 0.99
    assert no_lag_sharpe > 10.0

    # Met lag verdwijnt het volledig.
    assert abs(lagged_sharpe) < 1.0
    assert no_lag_sharpe > lagged_sharpe * 5


def test_positions_are_shifted_before_earning_returns() -> None:
    """De uitgevoerde positie loopt precies één dag achter.

    Controleert de mechaniek expliciet in plaats van op het resultaat te
    vertrouwen.
    """
    index = make_index(20)
    returns = pd.Series(np.arange(20, dtype=float) * 0.001, index=index)
    positions = pd.Series(np.arange(20, dtype=float), index=index)

    result = run_backtest(positions, returns, execution_lag=1)

    # Op elke dag is de uitgevoerde positie die van de vorige dag.
    for date in result.executed_positions.dropna().index[:5]:
        previous = positions.index[positions.index.get_loc(date) - 1]
        assert result.executed_positions.loc[date] == positions.loc[previous]


def test_longer_lag_reduces_a_genuine_signal() -> None:
    """Een echt signaal verzwakt naarmate je later uitvoert.

    Positieve controle op de laggingmechaniek: met een ingebouwd
    voorspellend signaal moet lag 1 beter zijn dan lag 5, want het signaal
    veroudert.
    """
    index = make_index(2000)
    rng = np.random.default_rng(3)
    driver = rng.standard_normal(2000)
    # Rendement van dag t hangt af van de driver van dag t-1.
    returns_values = np.empty(2000)
    returns_values[0] = 0.0
    returns_values[1:] = 0.6 * driver[:-1] * 0.01 + rng.standard_normal(1999) * 0.004
    returns = pd.Series(returns_values, index=index)
    positions = pd.Series(np.sign(driver), index=index)

    fast = run_backtest(positions, returns, execution_lag=1)
    slow = run_backtest(positions, returns, execution_lag=5)

    assert fast.metrics["gross"]["sharpe"] > slow.metrics["gross"]["sharpe"]


# -- kosten ---------------------------------------------------------------


def test_costs_reduce_returns() -> None:
    """Het nettoresultaat is altijd lager dan het brutoresultaat."""
    index = make_index(500)
    rng = np.random.default_rng(4)
    returns = pd.Series(rng.standard_normal(500) * 0.01, index=index)
    positions = pd.Series(rng.choice([-1.0, 1.0], 500), index=index)

    result = run_backtest(positions, returns)

    assert result.net_returns.sum() < result.gross_returns.sum()
    assert (result.costs >= 0).all()


def test_no_trading_means_no_costs() -> None:
    """Een constante positie na de opbouw kost niets extra."""
    index = make_index(500)
    rng = np.random.default_rng(5)
    returns = pd.Series(rng.standard_normal(500) * 0.01, index=index)
    positions = pd.Series(1.0, index=index)

    result = run_backtest(positions, returns)

    # Alleen de allereerste dag heeft omzet (opbouw van de positie).
    assert float(result.costs.iloc[1:].sum()) == pytest.approx(0.0, abs=1e-12)


def test_more_trading_costs_more() -> None:
    """Een strategie die vaker wisselt, betaalt meer."""
    index = make_index(1000)
    rng = np.random.default_rng(6)
    returns = pd.Series(rng.standard_normal(1000) * 0.01, index=index)

    calm = pd.Series(np.repeat([1.0, -1.0], 500), index=index)
    frantic = pd.Series(rng.choice([-1.0, 1.0], 1000), index=index)

    calm_result = run_backtest(calm, returns)
    frantic_result = run_backtest(frantic, returns)

    assert frantic_result.costs.sum() > calm_result.costs.sum() * 10


def test_cost_model_components_add_up() -> None:
    """De totale kosten zijn de som van de onderdelen."""
    model = CostModel(commission_bps=1.0, half_spread_bps=2.0, slippage_bps=3.0)

    assert model.total_bps == pytest.approx(6.0)
    assert model.total_fraction == pytest.approx(0.0006)


# -- signaal --------------------------------------------------------------


def test_sign_method_produces_full_positions() -> None:
    """De 'sign'-methode gaat altijd voluit."""
    predictions = pd.Series([0.01, -0.02, 0.005], index=make_index(3))

    positions = predictions_to_positions(
        predictions, SignalSettings(method="sign", max_position=1.0)
    )

    assert set(positions.unique()) <= {-1.0, 1.0}


def test_threshold_method_stays_flat_on_weak_signals() -> None:
    """Onder de drempel wordt er niet gehandeld."""
    rng = np.random.default_rng(7)
    predictions = pd.Series(rng.standard_normal(1000) * 0.01, index=make_index(1000))

    positions = predictions_to_positions(
        predictions, SignalSettings(method="threshold", threshold_sigma=1.0)
    )

    # Bij een drempel van 1 sigma hoort ongeveer tweederde vlak te staan.
    assert 0.5 < float((positions == 0).mean()) < 0.85


def test_linear_method_respects_the_maximum() -> None:
    """De positie gaat nooit boven max_position."""
    rng = np.random.default_rng(8)
    predictions = pd.Series(rng.standard_normal(500) * 0.05, index=make_index(500))

    positions = predictions_to_positions(
        predictions, SignalSettings(method="linear", max_position=0.5)
    )

    assert float(positions.abs().max()) <= 0.5 + 1e-12


def test_turnover_counts_position_changes() -> None:
    """Omzet is de absolute verandering in de positie."""
    positions = pd.Series([1.0, 1.0, -1.0, 0.0], index=make_index(4))

    changes = turnover(positions)

    assert float(changes.iloc[0]) == pytest.approx(1.0)  # opbouw
    assert float(changes.iloc[1]) == pytest.approx(0.0)  # geen wijziging
    assert float(changes.iloc[2]) == pytest.approx(2.0)  # long naar short
    assert float(changes.iloc[3]) == pytest.approx(1.0)  # naar vlak


def test_position_statistics_report_market_participation() -> None:
    """De statistieken tellen hoe vaak er een positie open staat."""
    positions = pd.Series([1.0, 0.0, 0.0, -1.0], index=make_index(4))

    stats = position_statistics(positions)

    assert stats["n_days"] == 4
    assert stats["n_days_in_market"] == 2
    assert stats["share_in_market"] == pytest.approx(0.5)


# -- significantie en placebo ---------------------------------------------


def test_sharpe_significance_reports_the_hurdle() -> None:
    """De toets geeft aan welke Sharpe nodig is voor significantie.

    Bij 20 jaar data is de standaardfout ongeveer 0,22, dus een Sharpe onder
    0,44 is niet van nul te onderscheiden. Dat getal hoort bij elke
    gerapporteerde Sharpe, en ontbreekt in de meeste backtests.
    """
    rng = np.random.default_rng(9)
    n = 252 * 20
    returns = pd.Series(rng.standard_normal(n) * 0.01, index=make_index(n))

    outcome = sharpe_significance(returns)

    assert outcome["years"] == pytest.approx(20.0, rel=0.01)
    assert outcome["standard_error"] == pytest.approx(0.224, rel=0.05)
    # Pure ruis hoort niet significant te zijn.
    assert not outcome["significant"]


def test_sharpe_significance_detects_a_real_edge() -> None:
    """Een echt sterke strategie wordt wel als significant herkend."""
    rng = np.random.default_rng(10)
    n = 252 * 20
    # Dagelijks rendement met een duidelijke positieve drift.
    returns = pd.Series(
        rng.standard_normal(n) * 0.01 + 0.0008, index=make_index(n)
    )

    outcome = sharpe_significance(returns)

    assert outcome["significant"]
    assert outcome["t_statistic"] > 1.96


def test_placebo_backtest_flags_a_meaningless_strategy() -> None:
    """Een willekeurige positiereeks is niet te onderscheiden van geschud.

    De placebo die bij elke backtest hoort: schud de posities door de tijd en
    kijk of het echte resultaat eruit springt. Bij een strategie zonder
    signaal hoort dat niet zo te zijn.
    """
    index = make_index(2000)
    rng = np.random.default_rng(11)
    returns = pd.Series(rng.standard_normal(2000) * 0.01, index=index)
    positions = pd.Series(rng.choice([-1.0, 1.0], 2000), index=index)

    outcome = placebo_backtest(positions, returns, n_trials=100, seed=12)

    assert not outcome["distinguishable"]
    assert outcome["percentile_of_real"] < 95.0


def test_benchmarks_include_doing_nothing() -> None:
    """'Niets doen' staat als benchmark in de vergelijking.

    De belangrijkste benchmark, want een strategie die daar niet bovenuit
    komt heeft alleen kosten gemaakt.
    """
    index = make_index(500)
    rng = np.random.default_rng(13)
    returns = pd.Series(rng.standard_normal(500) * 0.01, index=index)
    positions = pd.Series(rng.choice([-1.0, 1.0], 500), index=index)

    result = run_backtest(positions, returns)
    table = compare_to_benchmarks(result, returns)

    assert "niets doen" in table.index
    assert float(table.loc["niets doen", "annual_return"]) == pytest.approx(0.0)
