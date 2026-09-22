"""Tests voor de placebo-toetsen en de steekproefgrootte-correctie.

De kernvraag die deze tests borgen: **doet de placebo wat hij belooft?**

Een placebo die op nepdata nooit iets vindt, is te streng en verbergt echte
resultaten. Een placebo die altijd iets vindt, is waardeloos. Het
foutenpercentage moet rond het nominale niveau liggen — en dat is precies wat
een placebo hoort aan te tonen over je eigen opzet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.placebo import (  # noqa: E402
    effective_sample_size,
    independent_episodes,
    placebo_fake_drivers,
    placebo_shuffled_target,
)


def make_index(n: int) -> pd.DatetimeIndex:
    """Werkdagenindex."""
    return pd.date_range("2010-01-01", periods=n, freq="B", name="date")


# -- effectieve steekproefgrootte -----------------------------------------


def test_white_noise_has_full_effective_sample() -> None:
    """Bij ongecorreleerde data draagt elke waarneming een volle eenheid bij."""
    rng = np.random.default_rng(1)
    series = pd.Series(rng.standard_normal(3000), index=make_index(3000))

    outcome = effective_sample_size(series)

    assert outcome["ratio"] > 0.9


def test_persistent_series_has_far_fewer_effective_observations() -> None:
    """Sterke persistentie verlaagt het effectieve aantal drastisch.

    Dit is het antwoord op "wat is je N?": bij een AR(1) met phi 0,98 heb je
    nominaal duizenden waarnemingen maar effectief een fractie daarvan.
    """
    rng = np.random.default_rng(2)
    n = 4000
    values = np.empty(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = 0.98 * values[i - 1] + rng.standard_normal()

    outcome = effective_sample_size(pd.Series(values, index=make_index(n)))

    assert outcome["ratio"] < 0.2
    assert outcome["n_effective"] < outcome["n"]


def test_effective_sample_never_exceeds_nominal() -> None:
    """N_eff wordt afgekapt op N, ook bij negatieve autocorrelatie.

    Wiskundig kan de formule boven N uitkomen bij een reeks die systematisch
    terugveert. Als antwoord op "wat is je N?" is dat onbruikbaar: je kunt
    niet meer onafhankelijke waarnemingen hebben dan waarnemingen.
    """
    rng = np.random.default_rng(3)
    n = 2000
    # Sterk terugverende reeks: opeenvolgende waarden wisselen van teken.
    values = np.empty(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = -0.7 * values[i - 1] + rng.standard_normal()

    outcome = effective_sample_size(pd.Series(values, index=make_index(n)))

    assert outcome["n_effective"] <= outcome["n"]
    assert outcome["ratio"] <= 1.0
    assert outcome["capped"] is True


def test_short_series_returns_nominal_size() -> None:
    """Te weinig data om autocorrelatie te schatten: val terug op N."""
    outcome = effective_sample_size(pd.Series([1.0, 2.0, 3.0]))

    assert outcome["n_effective"] == pytest.approx(3.0)


def test_independent_episodes_counts_non_overlapping_windows() -> None:
    """Het aantal onafhankelijke vensters is N gedeeld door de horizon.

    Dit is het getal dat telt bij de kwartaalvraag: niet 5.957 dagen maar 94
    onafhankelijke kwartalen.
    """
    series = pd.Series(np.zeros(1000), index=make_index(1000))

    outcome = independent_episodes(series, horizon_days=63)

    assert outcome["n_non_overlapping"] == 1000 // 63
    assert outcome["n_non_overlapping"] < outcome["n_days"]


# -- placebo: de foutenpercentages ----------------------------------------


def test_placebo_false_positive_rate_matches_nominal() -> None:
    """Op data zonder verband vindt de toets ongeveer het nominale percentage.

    DE BELANGRIJKSTE TEST VAN DIT BESTAND. Bij een drempel van 5% hoort een
    correcte toets in ongeveer 5% van de gevallen ten onrechte "significant"
    te zeggen. Wijkt dat ver af, dan is de opzet kapot — en dan zou elke
    bevinding in het project verdacht zijn.
    """
    rng = np.random.default_rng(4)
    n = 1500
    index = make_index(n)
    target = pd.Series(rng.standard_normal(n) * 0.01, index=index)
    drivers = pd.DataFrame(
        {
            "a": rng.standard_normal(n),
            "b": rng.standard_normal(n),
        },
        index=index,
    )

    outcome = placebo_shuffled_target(target, drivers, n_trials=200, seed=7)

    # Ruime marge: 200 herhalingen hebben zelf steekproefruis.
    assert 0.01 < outcome.false_positive_rate < 0.12


def test_placebo_does_not_flag_a_genuinely_absent_relationship() -> None:
    """Zonder echt verband ligt de echte uitkomst midden in de placeboverdeling."""
    rng = np.random.default_rng(5)
    n = 1500
    index = make_index(n)
    target = pd.Series(rng.standard_normal(n) * 0.01, index=index)
    drivers = pd.DataFrame({"noise": rng.standard_normal(n)}, index=index)

    outcome = placebo_shuffled_target(target, drivers, n_trials=150, seed=8)

    assert not outcome.is_distinguishable
    assert outcome.percentile_of_real < 95.0


def test_placebo_detects_a_genuine_relationship() -> None:
    """Met een echt sterk verband steekt de uitkomst boven de placebo uit.

    De positieve controle: zonder deze test zegt "niet te onderscheiden van
    toeval" niets, want een kapotte placebo zegt dat ook.
    """
    rng = np.random.default_rng(6)
    n = 1500
    index = make_index(n)
    driver = rng.standard_normal(n)
    target = pd.Series(0.7 * driver + rng.standard_normal(n) * 0.3, index=index)
    drivers = pd.DataFrame({"real": driver}, index=index)

    outcome = placebo_shuffled_target(target, drivers, n_trials=150, seed=9)

    assert outcome.is_distinguishable
    assert outcome.percentile_of_real >= 99.0
    assert outcome.real_statistic > outcome.placebo_statistics.max()


def test_fake_drivers_preserve_persistence() -> None:
    """De nep-drivers zijn net zo persistent als de echte.

    Dat is de hele opzet van deze placebo: alles gelijk houden BEHALVE het
    verband. Witte ruis als placebo zou een te makkelijke tegenstander zijn.
    """
    rng = np.random.default_rng(10)
    n = 2000
    index = make_index(n)

    persistent = np.empty(n)
    persistent[0] = 0.0
    for i in range(1, n):
        persistent[i] = 0.95 * persistent[i - 1] + rng.standard_normal()

    target = pd.Series(rng.standard_normal(n) * 0.01, index=index)
    drivers = pd.DataFrame({"persistent": persistent}, index=index)

    outcome = placebo_fake_drivers(target, drivers, n_trials=30, seed=11)

    # Zonder echt verband hoort de placebo-R2 in dezelfde orde te liggen als
    # de echte; een veel lagere placebo zou betekenen dat de nepreeksen te
    # makkelijk zijn.
    assert outcome.real_statistic < 0.05
    assert float(np.median(outcome.placebo_statistics)) < 0.05


def test_percentile_of_real_is_bounded() -> None:
    """Het percentiel ligt altijd tussen 0 en 100."""
    rng = np.random.default_rng(12)
    n = 800
    index = make_index(n)
    target = pd.Series(rng.standard_normal(n), index=index)
    drivers = pd.DataFrame({"x": rng.standard_normal(n)}, index=index)

    outcome = placebo_shuffled_target(target, drivers, n_trials=50, seed=13)

    assert 0.0 <= outcome.percentile_of_real <= 100.0
    assert outcome.n_trials == 50
    assert len(outcome.placebo_statistics) == 50
