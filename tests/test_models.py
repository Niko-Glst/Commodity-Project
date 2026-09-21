"""Tests voor de regressiemodellen en de walk-forward validatie.

De belangrijkste tests hier zijn twee positieve controles:

1. Als er ECHT een verband in de data zit, moet de walk-forward dat vinden en
   de random walk verslaan.
2. Als er GEEN verband is, moet hij dat ook zeggen.

Zonder de eerste betekent "het model verslaat de benchmark niet" niets — een
kapotte validatie zegt dat ook. Dat onderscheid is het verschil tussen een
resultaat en een bug, en fase 3 rust er volledig op.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.models import (  # noqa: E402
    compute_vif,
    diebold_mariano,
    fit_ols_newey_west,
    walk_forward_validate,
)


def make_index(n: int) -> pd.DatetimeIndex:
    """Werkdagenindex van n dagen."""
    return pd.date_range("2010-01-01", periods=n, freq="B", name="date")


# -- OLS en Newey-West ----------------------------------------------------


def test_recovers_a_known_coefficient() -> None:
    """Op verzonnen data met een bekend verband vindt OLS de juiste waarde."""
    rng = np.random.default_rng(1)
    n = 2000
    index = make_index(n)
    driver = pd.Series(rng.standard_normal(n), index=index, name="driver")
    target = pd.Series(
        2.5 * driver.to_numpy() + rng.standard_normal(n) * 0.5,
        index=index,
        name="target",
    )

    result = fit_ols_newey_west(target, driver.to_frame())

    assert result.coefficients["driver"] == pytest.approx(2.5, abs=0.05)
    assert result.r_squared > 0.9


def test_newey_west_does_not_change_coefficients() -> None:
    """De correctie raakt de standaardfouten, niet de schattingen.

    Dit is een veelgemaakt misverstand: Newey-West maakt het model niet
    beter, alleen de onzekerheid eerlijker.
    """
    rng = np.random.default_rng(2)
    n = 1500
    index = make_index(n)
    driver = pd.DataFrame({"x": rng.standard_normal(n)}, index=index)
    target = pd.Series(driver["x"].to_numpy() + rng.standard_normal(n), index=index)

    import statsmodels.api as sm

    plain = sm.OLS(target, sm.add_constant(driver)).fit()
    result = fit_ols_newey_west(target, driver)

    assert result.coefficients["x"] == pytest.approx(plain.params["x"])


def _autocorrelated_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    """Fouten met wisselende variantie én autocorrelatie.

    Bootst het patroon uit fase 1 na: een rustige en een onrustige helft,
    met persistentie binnen elke helft.
    """
    noise = np.empty(n)
    noise[0] = 0.0
    scale = np.where(np.arange(n) < n // 2, 0.2, 2.0)
    for i in range(1, n):
        noise[i] = 0.7 * noise[i - 1] + rng.standard_normal() * scale[i]
    return noise


def test_newey_west_inflates_errors_with_a_persistent_driver() -> None:
    """Bij een persistente driver én gecorreleerde fouten groeien de fouten.

    Dit is de situatie in de echte data: rentes en de dollarindex zijn sterk
    persistent, en de residuen clusteren. Gemeten inflatie op het echte
    goudmodel: 1,66 tot 1,81 keer.
    """
    rng = np.random.default_rng(3)
    n = 2000
    index = make_index(n)

    # Persistente driver, zoals een renteniveau.
    persistent = np.empty(n)
    persistent[0] = 0.0
    for i in range(1, n):
        persistent[i] = 0.95 * persistent[i - 1] + rng.standard_normal()

    driver = pd.DataFrame({"x": persistent}, index=index)
    target = pd.Series(persistent + _autocorrelated_noise(n, rng), index=index)

    result = fit_ols_newey_west(target, driver)

    assert result.se_inflation["x"] > 1.3


def test_newey_west_barely_moves_with_an_independent_driver() -> None:
    """Bij een onafhankelijke driver verandert de correctie vrijwel niets.

    Dit legt een eigenschap vast die makkelijk verkeerd begrepen wordt:
    Newey-West blaast de standaardfouten alleen op als ZOWEL de driver ALS
    de fout gecorreleerd zijn over tijd. Bij witte-ruis-drivers heffen de
    kruistermen elkaar op, ook al zijn de fouten zelf sterk
    geautocorreleerd en heteroskedastisch.

    Het is dus niet "clusterende volatiliteit betekent altijd grotere
    standaardfouten" — het hangt van de driver af. Ik ben hier bij het
    schrijven van deze test zelf in getrapt.
    """
    rng = np.random.default_rng(3)
    n = 2000
    index = make_index(n)

    white_noise_driver = rng.standard_normal(n)
    driver = pd.DataFrame({"x": white_noise_driver}, index=index)
    target = pd.Series(
        white_noise_driver + _autocorrelated_noise(n, rng), index=index
    )

    result = fit_ols_newey_west(target, driver)

    assert 0.85 < result.se_inflation["x"] < 1.15


def test_vif_is_one_for_independent_drivers() -> None:
    """Onafhankelijke variabelen hebben een VIF rond 1."""
    rng = np.random.default_rng(4)
    design = pd.DataFrame(
        {
            "a": rng.standard_normal(2000),
            "b": rng.standard_normal(2000),
            "c": rng.standard_normal(2000),
        }
    )
    vif = compute_vif(design)

    assert all(value < 1.1 for value in vif)


def test_vif_explodes_for_duplicated_drivers() -> None:
    """Twee bijna identieke drivers geven een hoge VIF.

    Dit is het probleem uit fase 2 bevinding 6: de twee dollarmaatstaven
    correleren 0,74, en dat maakt de losse coëfficiënten onbetrouwbaar.
    """
    rng = np.random.default_rng(5)
    base = rng.standard_normal(2000)
    design = pd.DataFrame(
        {
            "a": base,
            "a_copy": base + rng.standard_normal(2000) * 0.05,
            "b": rng.standard_normal(2000),
        }
    )
    vif = compute_vif(design)

    assert vif["a"] > 10
    assert vif["a_copy"] > 10
    assert vif["b"] < 1.1


# -- walk-forward: de positieve controle ----------------------------------


def test_walk_forward_finds_a_real_signal() -> None:
    """Zit er echt voorspelkracht in, dan verslaat OLS de random walk.

    DE BELANGRIJKSTE TEST VAN FASE 3. De driver van gisteren voorspelt hier
    per constructie het rendement van vandaag. Vindt de validatie dat niet,
    dan is elke conclusie over "geen signaal" waardeloos.
    """
    rng = np.random.default_rng(6)
    n = 2500
    index = make_index(n)
    driver_values = rng.standard_normal(n)

    # Het rendement van dag t hangt af van de driver van dag t-1.
    target_values = np.empty(n)
    target_values[0] = 0.0
    target_values[1:] = 0.8 * driver_values[:-1] + rng.standard_normal(n - 1) * 0.3

    target = pd.Series(target_values, index=index)
    drivers = pd.DataFrame({"signal": driver_values}, index=index)

    result = walk_forward_validate(target, drivers, min_train=800, step=50)

    ols_rmse = float(result.metrics.loc["ols", "rmse"])
    benchmark_rmse = float(result.metrics.loc["random_walk", "rmse"])

    assert ols_rmse < benchmark_rmse, "de validatie vindt een echt signaal niet"
    assert float(result.metrics.loc["ols", "r2_oos"]) > 0.5
    assert float(result.metrics.loc["ols", "directional_accuracy"]) > 0.8


def test_walk_forward_finds_nothing_in_noise() -> None:
    """Zonder verband verslaat OLS de random walk niet.

    De negatieve controle. Samen met de test hierboven weet je dat de
    uitkomst op de echte data betekenis heeft.
    """
    rng = np.random.default_rng(7)
    n = 2500
    index = make_index(n)
    target = pd.Series(rng.standard_normal(n) * 0.01, index=index)
    drivers = pd.DataFrame(
        {"noise_a": rng.standard_normal(n), "noise_b": rng.standard_normal(n)},
        index=index,
    )

    result = walk_forward_validate(target, drivers, min_train=800, step=50)

    assert float(result.metrics.loc["ols", "rmse"]) >= float(
        result.metrics.loc["random_walk", "rmse"]
    )
    assert float(result.metrics.loc["ols", "r2_oos"]) <= 0.01


def test_walk_forward_lags_the_drivers() -> None:
    """De drivers worden gelagd, dus gelijktijdige samenhang helpt niet.

    Cruciaal tegen look-ahead bias: een driver die alleen SAMEN met het doel
    beweegt maar niet vooruitloopt, mag out-of-sample niets opleveren.
    """
    rng = np.random.default_rng(8)
    n = 2500
    index = make_index(n)
    shock = rng.standard_normal(n)

    # Doel en driver bewegen op DEZELFDE dag, zonder voorlooprelatie.
    target = pd.Series(shock * 0.01, index=index)
    drivers = pd.DataFrame({"same_day": shock}, index=index)

    result = walk_forward_validate(target, drivers, min_train=800, step=50)

    # Zonder lag zou dit een R² van bijna 1 geven; met lag vrijwel niets.
    assert float(result.metrics.loc["ols", "r2_oos"]) < 0.05


def test_random_walk_predicts_exactly_zero() -> None:
    """De benchmark voorspelt nul, en heeft dus geen richting."""
    rng = np.random.default_rng(9)
    n = 1500
    index = make_index(n)
    target = pd.Series(rng.standard_normal(n) * 0.01, index=index)
    drivers = pd.DataFrame({"x": rng.standard_normal(n)}, index=index)

    result = walk_forward_validate(target, drivers, min_train=800, step=50)

    assert (result.predictions["random_walk"] == 0.0).all()
    # Nul heeft geen teken, dus directional accuracy is niet van toepassing.
    assert pd.isna(result.metrics.loc["random_walk", "directional_accuracy"])
    # En de out-of-sample R² van de benchmark is per definitie nul.
    assert float(result.metrics.loc["random_walk", "r2_oos"]) == pytest.approx(0.0)


def test_no_training_data_leaks_from_the_future() -> None:
    """Data na het voorspelmoment beïnvloedt de voorspelling niet.

    We vervangen de tweede helft van de reeks door onzin. De voorspellingen
    voor de EERSTE helft moeten identiek blijven; veranderen ze, dan traint
    het model op toekomstige data.
    """
    rng = np.random.default_rng(10)
    n = 2000
    index = make_index(n)
    driver_values = rng.standard_normal(n)
    target_values = 0.5 * np.concatenate([[0.0], driver_values[:-1]]) + rng.standard_normal(n) * 0.5

    clean_target = pd.Series(target_values, index=index)
    clean_drivers = pd.DataFrame({"x": driver_values}, index=index)

    corrupted_target = clean_target.copy()
    corrupted_target.iloc[1500:] = 999.0
    corrupted_drivers = clean_drivers.copy()
    corrupted_drivers.iloc[1500:] = -999.0

    clean = walk_forward_validate(clean_target, clean_drivers, min_train=800, step=50)
    dirty = walk_forward_validate(
        corrupted_target, corrupted_drivers, min_train=800, step=50
    )

    # Vergelijk alleen de voorspellingen van vóór de corruptie.
    cutoff = index[1400]
    clean_early = clean.predictions.loc[:cutoff, "ols"]
    dirty_early = dirty.predictions.loc[:cutoff, "ols"]

    assert len(clean_early) > 5
    pd.testing.assert_series_equal(clean_early, dirty_early)


# -- Diebold-Mariano ------------------------------------------------------


def test_diebold_mariano_detects_a_clear_winner() -> None:
    """Bij een duidelijk beter model is het verschil significant."""
    rng = np.random.default_rng(11)
    n = 800
    actual = pd.Series(rng.standard_normal(n))
    good = actual + rng.standard_normal(n) * 0.2
    bad = pd.Series(rng.standard_normal(n) * 2)

    test = diebold_mariano(actual, good, bad)

    assert test["p_value"] < 0.05
    assert test["better"] == "eerste model"


def test_diebold_mariano_finds_no_difference_between_equals() -> None:
    """Twee even goede modellen leveren geen significant verschil op."""
    rng = np.random.default_rng(12)
    n = 800
    actual = pd.Series(rng.standard_normal(n))
    first = actual + rng.standard_normal(n)
    second = actual + rng.standard_normal(n)

    test = diebold_mariano(actual, first, second)

    assert test["better"] == "geen significant verschil"


def test_diebold_mariano_handles_short_series() -> None:
    """Te weinig waarnemingen geeft 'onbepaald' in plaats van een crash."""
    actual = pd.Series([1.0, 2.0, 3.0])
    test = diebold_mariano(actual, actual, actual)

    assert test["better"] == "onbepaald"
    assert np.isnan(test["statistic"])
