"""Tests voor de dekkingstoetsen.

De kernvraag: **weet de toets een goed model van een slecht model te
onderscheiden?** Een toets die alles goedkeurt is waardeloos, en een toets die
alles afkeurt ook. Deze tests bouwen daarom data waarvan het antwoord vooraf
vaststaat, en controleren of de toets dat antwoord vindt.

Eén test is bewust omgekeerd: hij legt vast dat de toets bij realistische
aantallen GEEN kracht heeft. Dat is geen bug maar de reden waarom overal het
label UNDERPOWERED bij staat.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.validation import (  # noqa: E402
    christoffersen_independence_test,
    evaluate_coverage,
    ewma_buffer,
    fixed_buffer,
    kupiec_pof_test,
    rolling_percentile_buffer,
)


def make_index(n: int) -> pd.DatetimeIndex:
    """Werkdagenindex."""
    return pd.date_range("2010-01-01", periods=n, freq="B", name="date")


# -- Kupiec ----------------------------------------------------------------


def test_kupiec_accepts_correct_breach_rate() -> None:
    """Precies het verwachte aantal overschrijdingen mag niet afgewezen worden."""
    # 1000 perioden op 99% - verwacht 10 overschrijdingen.
    _, p_value = kupiec_pof_test(n_periods=1000, n_breaches=10, confidence=0.99)
    assert p_value > 0.9


def test_kupiec_rejects_far_too_many_breaches() -> None:
    """Vijf keer te veel overschrijdingen moet wél afgewezen worden."""
    _, p_value = kupiec_pof_test(n_periods=1000, n_breaches=50, confidence=0.99)
    assert p_value < 0.001


def test_kupiec_rejects_far_too_few_breaches() -> None:
    """Nul overschrijdingen op 1000 perioden is ook verkeerd.

    Te weinig overschrijdingen betekent een te conservatieve buffer: geen
    risico, maar wel onnodig vastgelegd kapitaal. De toets is tweezijdig en
    hoort dit ook op te merken.
    """
    _, p_value = kupiec_pof_test(n_periods=1000, n_breaches=0, confidence=0.99)
    assert p_value < 0.001


def test_kupiec_handles_zero_periods() -> None:
    """Zonder data geen uitspraak - geen crash, maar NaN."""
    statistic, p_value = kupiec_pof_test(n_periods=0, n_breaches=0)
    assert np.isnan(statistic)
    assert np.isnan(p_value)


# -- de kracht van de toets ------------------------------------------------


def test_kupiec_is_powerless_at_realistic_sample_size() -> None:
    """DE BELANGRIJKSTE TEST: bij 78 kwartalen wijst Kupiec bijna niets af.

    Dit legt de beperking van het hele project vast. Bij 78 perioden op 99%
    verwacht je 0,78 overschrijdingen. Een model met nul overschrijdingen en
    een met drie - een factor vier verschil in werkelijk risico - zijn allebei
    verenigbaar met de nulhypothese.

    Zolang deze test slaagt, is elke p-waarde in de dekkingstabel indicatief
    en niet beslissend.
    """
    for n_breaches in (0, 1, 2, 3):
        _, p_value = kupiec_pof_test(
            n_periods=78, n_breaches=n_breaches, confidence=0.99
        )
        assert p_value > 0.05, (
            f"{n_breaches} overschrijdingen wordt afgewezen; als dat zo is "
            f"heeft de toets meer kracht dan gedacht en mag de "
            f"UNDERPOWERED-waarschuwing herzien worden"
        )


def test_result_flags_underpowered_on_expected_breaches() -> None:
    """Het label kijkt naar verwachte gebeurtenissen, niet naar perioden.

    500 perioden klinkt ruim, maar op 99% zijn dat 5 verwachte
    overschrijdingen. Dat is de grens.
    """
    # 200 perioden: ruim boven de perioden-drempel van 30, maar op 99% zijn
    # dat maar 2 verwachte overschrijdingen. Het label moet op het tweede
    # getal afgaan.
    index = make_index(200)
    buffers = pd.Series(0.25, index=index)
    realised = pd.Series(0.05, index=index)
    result = evaluate_coverage(buffers, realised, label="test", confidence=0.99)

    assert result.n_periods == 200
    assert result.n_periods > 30  # zou op zichzelf "genoeg" lijken
    assert np.isclose(result.expected_breaches, 2.0)
    assert result.is_underpowered  # maar 2 verwachte gebeurtenissen is te weinig

    # Bij een lagere drempel leveren dezelfde 200 perioden 20 verwachte
    # overschrijdingen op, en dan is er wel kracht.
    ruimer = evaluate_coverage(buffers, realised, label="test", confidence=0.90)
    assert np.isclose(ruimer.expected_breaches, 20.0)
    assert not ruimer.is_underpowered


def test_few_periods_are_underpowered_even_at_low_confidence() -> None:
    """Onder de 30 perioden is elk resultaat onderbemeten."""
    index = make_index(20)
    buffers = pd.Series(0.25, index=index)
    realised = pd.Series(0.05, index=index)
    result = evaluate_coverage(buffers, realised, label="test", confidence=0.90)
    assert result.is_underpowered


# -- Christoffersen --------------------------------------------------------


def test_christoffersen_accepts_spread_out_breaches() -> None:
    """Gelijkmatig verspreide overschrijdingen zijn onafhankelijk."""
    breaches = np.zeros(200, dtype=int)
    breaches[::20] = 1  # elke 20e periode
    _, p_value = christoffersen_independence_test(breaches)
    assert p_value > 0.05


def test_christoffersen_rejects_clustered_breaches() -> None:
    """Op een hoop geclusterde overschrijdingen moeten afgewezen worden.

    Dit is het patroon dat je krijgt als een model volatiliteitsclustering
    negeert: het gaat pas stuk als het al stuk is, en dan meteen een tijd
    achter elkaar.
    """
    breaches = np.zeros(200, dtype=int)
    breaches[100:110] = 1  # tien op rij
    _, p_value = christoffersen_independence_test(breaches)
    assert p_value < 0.05


def test_christoffersen_returns_nan_without_breaches() -> None:
    """Zonder overschrijdingen valt er niets over timing te zeggen."""
    statistic, p_value = christoffersen_independence_test(np.zeros(100, dtype=int))
    assert np.isnan(statistic)
    assert np.isnan(p_value)


# -- de bufferregels -------------------------------------------------------


def test_fixed_buffer_is_constant() -> None:
    """De vuistregel doet per definitie niets met de markt."""
    index = make_index(50)
    buffers = fixed_buffer(index, level=0.25)
    assert (buffers == 0.25).all()
    assert len(buffers) == 50


def test_rolling_percentile_uses_only_prior_data() -> None:
    """GEEN LOOK-AHEAD: een buffer mag niets van zijn eigen toekomst weten.

    De test: zet na het beslismoment een extreme uitschieter in de data. Als
    de buffer daarop reageert, lekt toekomstige informatie naar binnen.
    """
    index = make_index(1500)
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(0, 0.01, 1500), index=index)

    decision_date = index[1000]
    starts = pd.Index([decision_date])

    before = rolling_percentile_buffer(returns, starts, horizon_days=63)

    # Zelfde reeks, maar met een crash NA het beslismoment.
    contaminated = returns.copy()
    contaminated.iloc[1100:1120] = -0.15
    after = rolling_percentile_buffer(contaminated, starts, horizon_days=63)

    assert np.isclose(before.iloc[0], after.iloc[0]), (
        "de buffer veranderde door data van NA het beslismoment - "
        "dat is look-ahead bias"
    )


def test_ewma_buffer_responds_to_recent_volatility() -> None:
    """EWMA hoort juist wél te reageren op recente - eerdere - volatiliteit.

    Het spiegelbeeld van de vorige test: informatie van vóór het
    beslismoment moet wel degelijk doorwerken, anders is het model dood.
    """
    index = make_index(1500)
    rng = np.random.default_rng(7)
    calm = pd.Series(rng.normal(0, 0.005, 1500), index=index)

    turbulent = calm.copy()
    turbulent.iloc[900:1000] = rng.normal(0, 0.04, 100)

    starts = pd.Index([index[1000]])
    calm_buffer = ewma_buffer(calm, starts, horizon_days=63)
    turbulent_buffer = ewma_buffer(turbulent, starts, horizon_days=63)

    assert turbulent_buffer.iloc[0] > calm_buffer.iloc[0]


# -- de toets van begin tot eind -------------------------------------------


def test_coverage_counts_breaches_correctly() -> None:
    """Een overschrijding is realised > buffer, niets ingewikkelders."""
    index = make_index(100)
    buffers = pd.Series(0.10, index=index)
    realised = pd.Series(0.05, index=index)
    realised.iloc[[10, 50, 90]] = 0.20  # drie duidelijke overschrijdingen

    result = evaluate_coverage(buffers, realised, label="test", confidence=0.99)

    assert result.n_periods == 100
    assert result.n_breaches == 3
    assert len(result.breach_dates) == 3


def test_coverage_reports_buffer_cost() -> None:
    """De gemiddelde buffer is de prijs van de dekking en moet kloppen."""
    index = make_index(100)
    buffers = pd.Series(np.linspace(0.10, 0.30, 100), index=index)
    realised = pd.Series(0.01, index=index)

    result = evaluate_coverage(buffers, realised, label="test")

    assert np.isclose(result.mean_buffer, 0.20, atol=0.01)
    assert np.isclose(result.max_buffer, 0.30, atol=0.01)


def test_coverage_aligns_on_dates() -> None:
    """Buffers en uitkomsten worden op datum gekoppeld, niet op positie.

    Bij ongelijke indices moet de toets de doorsnede nemen. Anders vergelijk
    je een buffer met de uitkomst van een ander kwartaal.
    """
    index = make_index(100)
    buffers = pd.Series(0.10, index=index)
    realised = pd.Series(0.05, index=index[:60])  # korter

    result = evaluate_coverage(buffers, realised, label="test")
    assert result.n_periods == 60
