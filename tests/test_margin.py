"""Tests voor de margeboekhouding.

Dit is boekhouding, geen statistiek: de getallen moeten exact kloppen. Een
fout van 1% in een statistische schatting is ruis, een fout van 1% in een
margeberekening is een verkeerd antwoord op de vraag waar dit project om
draait.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.margin import (  # noqa: E402
    CONTRACT_SIZE_OUNCES,
    MarginSettings,
    buffer_needed_for_confidence,
    simulate_margin,
)


def make_prices(values: list[float]) -> pd.Series:
    """Bouwt een koersreeks met een datumindex."""
    return pd.Series(
        values, index=pd.date_range("2024-01-01", periods=len(values), freq="B")
    )


# -- de basisboekhouding --------------------------------------------------


def test_initial_margin_is_percentage_of_notional() -> None:
    """De initial margin is het afgesproken percentage van de notionele waarde."""
    prices = make_prices([2000.0, 2000.0])
    result = simulate_margin(prices, MarginSettings(initial_margin_pct=0.05))

    assert result.notional_start == 2000.0 * CONTRACT_SIZE_OUNCES
    assert result.initial_margin == pytest.approx(200_000.0 * 0.05)


def test_short_loses_when_price_rises() -> None:
    """Een short verliest bij een stijging, en precies het prijsverschil."""
    prices = make_prices([2000.0, 2010.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    # 10 dollar stijging x 100 ounce = 1000 dollar verlies.
    assert result.days[0].daily_pnl == pytest.approx(-1000.0)


def test_long_gains_when_price_rises() -> None:
    """Een long wint bij een stijging, spiegelbeeldig aan de short."""
    prices = make_prices([2000.0, 2010.0])
    result = simulate_margin(prices, MarginSettings(is_short=False))

    assert result.days[0].daily_pnl == pytest.approx(1000.0)


def test_pnl_scales_with_contracts() -> None:
    """Twee contracten geven precies het dubbele resultaat."""
    prices = make_prices([2000.0, 2010.0])
    one = simulate_margin(prices, MarginSettings(contracts=1))
    two = simulate_margin(prices, MarginSettings(contracts=2))

    assert two.days[0].daily_pnl == pytest.approx(one.days[0].daily_pnl * 2)
    assert two.initial_margin == pytest.approx(one.initial_margin * 2)


def test_net_loss_equals_price_move() -> None:
    """Het nettoverlies is exact de prijsbeweging maal het aantal ounces.

    Dit is de belangrijkste controle op de boekhouding: hoeveel je onderweg
    ook hebt bijgestort en teruggekregen, wat je uiteindelijk kwijt bent is
    gewoon het prijsverschil. Klopt dat niet, dan lekt er ergens geld weg in
    de berekening.
    """
    prices = make_prices([2000.0, 2100.0, 2050.0, 2200.0, 2150.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    expected = (float(prices.iloc[-1]) - float(prices.iloc[0])) * CONTRACT_SIZE_OUNCES
    assert result.net_loss == pytest.approx(expected)


def test_no_margin_call_when_price_moves_in_your_favour() -> None:
    """Bij een gunstige beweging is er geen enkele margin call."""
    prices = make_prices([2000.0, 1950.0, 1900.0, 1850.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    assert result.n_margin_calls == 0
    assert result.peak_cash_needed == pytest.approx(0.0)


def test_margin_call_tops_up_to_initial_not_maintenance() -> None:
    """Een margin call vult aan tot de INITIAL margin, niet tot de ondergrens.

    Dat onderscheid is geen detail: het betekent dat een call altijd meer
    vraagt dan het tekort dat je op dat moment hebt.
    """
    settings = MarginSettings(initial_margin_pct=0.05, maintenance_pct=0.045)
    prices = make_prices([2000.0, 2050.0])
    result = simulate_margin(prices, settings)

    day = result.days[0]
    required = day.price * CONTRACT_SIZE_OUNCES * settings.initial_margin_pct

    assert day.margin_call > 0
    assert day.balance_after_call == pytest.approx(required)
    # De aanvulling gaat verder dan de ondergrens.
    assert day.balance_after_call > day.maintenance_level


def test_margin_requirement_rises_with_the_price() -> None:
    """Bij een short stijgt de vereiste mee met de prijs: dubbel nadeel."""
    prices = make_prices([2000.0, 2400.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    day = result.days[0]
    # De ondergrens hoort bij de NIEUWE, hogere prijs.
    assert day.maintenance_level == pytest.approx(
        2400.0 * CONTRACT_SIZE_OUNCES * 0.045
    )
    assert day.maintenance_level > 2000.0 * CONTRACT_SIZE_OUNCES * 0.045


def test_balance_never_ends_below_maintenance_after_call() -> None:
    """Na afhandeling staat het saldo nooit onder de ondergrens."""
    rng = np.random.default_rng(3)
    path = 2000.0 * np.exp(np.cumsum(rng.normal(0.002, 0.02, 200)))
    result = simulate_margin(make_prices(list(path)), MarginSettings())

    for day in result.days:
        assert day.balance_after_call >= day.maintenance_level - 1e-6


def test_peak_cash_exceeds_net_loss_when_price_recovers() -> None:
    """Gestort geld dat terugkomt telt wel voor de buffer, niet voor het verlies.

    Scenario: de prijs schiet omhoog (margin call), en zakt daarna terug. Je
    moest wel storten, maar je bent het niet kwijt.
    """
    prices = make_prices([2000.0, 2300.0, 2000.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    assert result.n_margin_calls >= 1
    assert result.peak_cash_needed > 0
    # Prijs is terug op het startniveau, dus per saldo geen verlies.
    assert result.net_loss == pytest.approx(0.0, abs=1e-6)
    assert result.peak_cash_needed > result.net_loss


def test_requires_at_least_two_prices() -> None:
    """Met één koers valt er niets te herrekenen."""
    with pytest.raises(ValueError, match="Minstens twee koersen"):
        simulate_margin(make_prices([2000.0]))


# -- de bufferberekening --------------------------------------------------


def test_buffer_percentiles_are_ordered() -> None:
    """Mediaan <= 99%-grens <= ergste geval."""
    rng = np.random.default_rng(5)
    returns = pd.Series(
        rng.normal(0.0002, 0.012, 1500),
        index=pd.date_range("2018-01-01", periods=1500, freq="B"),
    )

    outcome = buffer_needed_for_confidence(
        returns, horizon_days=21, confidence=0.99, n_windows=200
    )

    assert outcome["median_pct"] <= outcome["buffer_pct"]
    assert outcome["buffer_pct"] <= outcome["worst_pct"]
    assert 0.0 <= outcome["share_with_margin_call"] <= 1.0


def test_longer_horizon_needs_more_buffer() -> None:
    """Een langere periode overbruggen vraagt meer cash."""
    rng = np.random.default_rng(7)
    returns = pd.Series(
        rng.normal(0.0002, 0.012, 2000),
        index=pd.date_range("2016-01-01", periods=2000, freq="B"),
    )

    week = buffer_needed_for_confidence(
        returns, horizon_days=5, confidence=0.99, n_windows=200
    )
    quarter = buffer_needed_for_confidence(
        returns, horizon_days=63, confidence=0.99, n_windows=200
    )

    assert quarter["buffer_pct"] > week["buffer_pct"]


def test_higher_confidence_needs_more_buffer() -> None:
    """Meer zekerheid kost meer kapitaal — de kernafweging."""
    rng = np.random.default_rng(11)
    returns = pd.Series(
        rng.normal(0.0002, 0.015, 1500),
        index=pd.date_range("2018-01-01", periods=1500, freq="B"),
    )

    at_95 = buffer_needed_for_confidence(
        returns, horizon_days=21, confidence=0.95, n_windows=200
    )
    at_99 = buffer_needed_for_confidence(
        returns, horizon_days=21, confidence=0.99, n_windows=200
    )

    assert at_99["buffer_pct"] > at_95["buffer_pct"]


def test_calm_market_needs_less_buffer_than_volatile() -> None:
    """Bij lagere volatiliteit is de benodigde buffer kleiner.

    Dit is de kern van het hele project: een vaste vuistregel negeert dat
    de behoefte met de marktomstandigheden meebeweegt.
    """
    rng = np.random.default_rng(13)
    index = pd.date_range("2018-01-01", periods=1200, freq="B")
    calm = pd.Series(rng.normal(0.0, 0.005, 1200), index=index)
    volatile = pd.Series(rng.normal(0.0, 0.025, 1200), index=index)

    calm_need = buffer_needed_for_confidence(
        calm, horizon_days=21, confidence=0.99, n_windows=200
    )
    volatile_need = buffer_needed_for_confidence(
        volatile, horizon_days=21, confidence=0.99, n_windows=200
    )

    assert volatile_need["buffer_pct"] > calm_need["buffer_pct"] * 2


def test_peak_cash_is_the_low_point_not_the_sum_of_deposits() -> None:
    """De piekbehoefte is het diepste punt, niet de som van alle stortingen.

    Scenario: de prijs schiet omhoog (storting nodig), zakt terug (geld komt
    terug op de rekening), en schiet weer omhoog (opnieuw storten). De som van
    de stortingen is dan veel groter dan wat je ooit tegelijk nodig had.

    Dit was een echte fout in dit project: over een kwartaal overschatte de
    som de werkelijke behoefte met zo'n 5 procentpunt.
    """
    prices = make_prices([2000.0, 2300.0, 2000.0, 2300.0, 2000.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    # Elke uitschieter naar 2300 kost 300 x 100 = 30.000 aan netto-inleg.
    assert result.peak_cash_needed == pytest.approx(30_000.0)
    # De som van alle stortingen is fors hoger, want er werd twee keer
    # gestort terwijl het geld tussendoor terugkwam.
    assert result.total_deposited - result.initial_margin > result.peak_cash_needed
    # En per saldo is er niets verloren: de prijs staat weer op de startwaarde.
    assert result.net_loss == pytest.approx(0.0, abs=1e-6)


def test_extra_cash_excludes_the_initial_margin() -> None:
    """extra_cash_needed telt niet mee wat je toch al gestort had."""
    prices = make_prices([2000.0, 2050.0])
    result = simulate_margin(prices, MarginSettings(is_short=True))

    assert result.extra_cash_needed == pytest.approx(
        max(result.peak_cash_needed - result.initial_margin, 0.0)
    )
    assert result.extra_cash_needed <= result.peak_cash_needed
