"""Tests voor de spectraalanalyse.

De belangrijkste test hier is ``test_detects_a_real_cycle``: als we een echte
sinus in de data stoppen, MOET de analyse hem vinden. Zonder die controle weet
je niet of "geen cyclus gevonden" betekent dat er geen cyclus is, of dat je
code kapot is. Dat onderscheid is het verschil tussen een resultaat en een bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from goldmodel.viz.spectral import (  # noqa: E402
    compute_periodogram,
    fit_sine,
    null_distribution,
    realised_volatility,
    spurious_cycle_from_smoothing,
)


# -- de detector werkt ----------------------------------------------------


def test_detects_a_real_cycle() -> None:
    """Een ingebouwde sinus van 50 stappen wordt teruggevonden.

    Dit is de positieve controle. Zonder deze test zegt "geen cyclus
    gevonden" niets, want een kapotte detector vindt ook niets.
    """
    rng = np.random.default_rng(1)
    t = np.arange(2000, dtype=float)
    signal_with_cycle = 3.0 * np.sin(2 * np.pi * t / 50.0) + rng.standard_normal(2000)

    periods, power = compute_periodogram(pd.Series(signal_with_cycle))
    detected = float(periods[np.argmax(power)])

    assert detected == pytest.approx(50.0, rel=0.05)


def test_fit_sine_recovers_a_pure_sine() -> None:
    """Op een zuivere sinus haalt de fit een zeer hoge R-kwadraat."""
    t = np.arange(1000, dtype=float)
    pure = pd.Series(2.0 * np.sin(2 * np.pi * t / 80.0 + 0.7))

    _, r_squared = fit_sine(pure, 80.0)

    assert r_squared > 0.99


def test_fit_sine_on_noise_gives_low_r_squared() -> None:
    """Op ruis verklaart een sinus vrijwel niets."""
    rng = np.random.default_rng(2)
    noise = pd.Series(rng.standard_normal(3000))

    _, r_squared = fit_sine(noise, 64.0)

    assert r_squared < 0.02


def test_wrong_period_fits_worse_than_right_period() -> None:
    """De juiste periode past beter dan een verkeerde."""
    t = np.arange(1500, dtype=float)
    series = pd.Series(np.sin(2 * np.pi * t / 60.0))

    _, correct = fit_sine(series, 60.0)
    _, wrong = fit_sine(series, 37.0)

    assert correct > wrong


# -- de referentieverdeling -----------------------------------------------


def test_ar1_null_preserves_persistence() -> None:
    """De AR(1)-referentie is net zo persistent als de echte reeks.

    Dit is de kern van de correctie: een geschudde referentie heeft geen
    persistentie en levert daarom vals alarm op lage frequenties.
    """
    rng = np.random.default_rng(3)
    n = 1500
    values = np.empty(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = 0.95 * values[i - 1] + rng.normal(0, 0.1)
    series = pd.Series(values + 10.0)

    ar1_sims = null_distribution(series, method="ar1", n_simulations=30)
    shuffled_sims = null_distribution(series, method="shuffle", n_simulations=30)

    # Op de laagste frequenties heeft een persistent proces veel meer
    # energie dan geschudde data.
    low_freq_ar1 = float(np.median(ar1_sims[:, :10]))
    low_freq_shuffled = float(np.median(shuffled_sims[:, :10]))

    assert low_freq_ar1 > low_freq_shuffled * 5


def test_shuffle_null_flags_persistence_as_cycle() -> None:
    """De geschudde referentie meldt ten onrechte structuur bij persistentie.

    Dit legt precies de fout vast die deze analyse bijna had gemaakt: op een
    persistente reeks ZONDER cyclus steekt het spectrum ver boven een
    geschudde band uit.
    """
    rng = np.random.default_rng(4)
    n = 1500
    values = np.empty(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = 0.97 * values[i - 1] + rng.normal(0, 0.1)
    series = pd.Series(values + 10.0)

    _, power = compute_periodogram(series)
    shuffled_band = np.percentile(
        null_distribution(series, method="shuffle", n_simulations=120), 95, axis=0
    )
    ar1_band = np.percentile(
        null_distribution(series, method="ar1", n_simulations=120), 95, axis=0
    )

    # Kijk naar de 30 laagste frequenties (de langste periodes): daar zit het
    # verschil, want daar heeft een persistente reeks van nature veel energie.
    low = slice(0, 30)
    n_tested = 30
    above_shuffled = int(np.sum(power[low] > shuffled_band[low]))
    above_ar1 = int(np.sum(power[low] > ar1_band[low]))

    # De geschudde referentie markeert de grote meerderheid van de lage
    # frequenties als "significant", in data waar per constructie geen cyclus
    # zit. Gemeten: ongeveer 87%.
    assert above_shuffled > n_tested * 0.6, (
        f"verwacht vals alarm op de lage frequenties, kreeg {above_shuffled}/{n_tested}"
    )
    # De AR(1)-referentie blijft in de buurt van de 5% die je bij toeval
    # verwacht, want die kent de persistentie al. Gemeten: ongeveer 7%.
    assert above_ar1 < n_tested * 0.25, (
        f"AR(1)-referentie geeft te veel vals alarm: {above_ar1}/{n_tested}"
    )


def test_null_distribution_rejects_unknown_method() -> None:
    """Een onbekende methode geeft een duidelijke fout."""
    series = pd.Series(np.arange(200, dtype=float))
    with pytest.raises(ValueError, match="Onbekende methode"):
        null_distribution(series, method="magie", n_simulations=2)


# -- het Slutsky-effect ---------------------------------------------------


def test_smoothing_creates_autocorrelation_from_nothing() -> None:
    """Gladstrijken maakt van onafhankelijke ruis een gecorreleerde reeks."""
    raw, smoothed = spurious_cycle_from_smoothing(n=4000, window=21)

    raw_autocorr = float(pd.Series(raw).autocorr(lag=1))
    smoothed_autocorr = float(pd.Series(smoothed).autocorr(lag=1))

    assert abs(raw_autocorr) < 0.05
    assert smoothed_autocorr > 0.8


# -- volatiliteit ---------------------------------------------------------


def test_realised_volatility_is_in_percentage_points() -> None:
    """De volatiliteit komt terug in procentpunten, niet als fractie.

    Een reeks met 1% dagbewegingen hoort op ongeveer 1 x sqrt(252) = 15,9%
    jaarvolatiliteit uit te komen, niet op 0,159. Dit is een echte fout
    geweest in dit project: de figuur toonde "5.2%" waar 5,25 bedoeld was.
    """
    rng = np.random.default_rng(6)
    returns = pd.Series(
        rng.normal(0, 0.01, 1000),
        index=pd.date_range("2020-01-01", periods=1000, freq="B"),
    )

    vol = realised_volatility(returns, window=21)

    assert 10.0 < float(vol.mean()) < 22.0


def test_realised_volatility_tracks_changing_regimes() -> None:
    """Een rustige en een onrustige periode leveren verschillende niveaus."""
    rng = np.random.default_rng(8)
    calm = rng.normal(0, 0.005, 500)
    wild = rng.normal(0, 0.03, 500)
    returns = pd.Series(
        np.concatenate([calm, wild]),
        index=pd.date_range("2020-01-01", periods=1000, freq="B"),
    )

    vol = realised_volatility(returns, window=21)

    assert float(vol.iloc[100:400].mean()) < float(vol.iloc[600:].mean())


# -- walk-forward ---------------------------------------------------------


def test_walk_forward_reports_all_benchmarks() -> None:
    """Alle benchmarks worden gerapporteerd, niet alleen de gunstigste.

    Een model vergelijken met een zelfgekozen zwakke benchmark is de
    makkelijkste manier om jezelf voor de gek te houden.
    """
    from analyse_cycles import walk_forward_sine_test

    rng = np.random.default_rng(12)
    series = pd.Series(15.0 + rng.standard_normal(1500).cumsum() * 0.05)

    result = walk_forward_sine_test(series, 64.0, horizon=21, min_train=800)

    for key in (
        "sine_rmse",
        "constant_only_rmse",
        "naive_last_rmse",
        "mean_all_rmse",
        "mean_recent_rmse",
    ):
        assert key in result
        assert result[key] > 0


def test_walk_forward_detects_a_genuine_cycle() -> None:
    """Zit er wél een sterke cyclus in, dan verslaat de sinus de benchmarks.

    De tegenhanger van de negatieve bevinding op de echte data: dit bewijst
    dat de test een cyclus zou vinden als die er was.
    """
    from analyse_cycles import walk_forward_sine_test

    rng = np.random.default_rng(13)
    t = np.arange(2000, dtype=float)
    cyclical = pd.Series(
        15.0 + 5.0 * np.sin(2 * np.pi * t / 64.0) + rng.normal(0, 0.5, 2000)
    )

    result = walk_forward_sine_test(cyclical, 64.0, horizon=21, min_train=1000)

    assert result["sine_beats_best_benchmark"]
    assert result["wave_contribution_pct"] > 50.0


def test_walk_forward_finds_nothing_in_a_pure_random_walk() -> None:
    """Op een random walk voegt de sinus niets toe.

    Een random walk is persistent maar heeft geen enkele cyclus. De golf
    hoort dan verwaarloosbaar of negatief bij te dragen.
    """
    from analyse_cycles import walk_forward_sine_test

    rng = np.random.default_rng(14)
    walk = pd.Series(15.0 + rng.standard_normal(2000).cumsum() * 0.05)

    result = walk_forward_sine_test(walk, 64.0, horizon=21, min_train=1000)

    assert result["wave_contribution_pct"] < 5.0
