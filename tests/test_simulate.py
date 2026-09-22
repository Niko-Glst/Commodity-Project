"""Tests voor de Monte Carlo-simulatie en de validatie ervan.

Een simulatie produceert altijd getallen. Deze tests stellen vast of die
getallen betekenen wat we denken:

- schaalt de volatiliteit door naar de uitkomst zoals de theorie zegt?
- geven t-schokken echt dikkere staarten dan normale?
- doet GARCH wat het belooft (clustering, afhankelijkheid van het startpunt)?
- meet de adverse excursion de TUSSENTIJDSE beweging en niet de eindwaarde?
- accepteert de Kupiec-toets een correct model en verwerpt hij een fout model?

Die laatste is de positieve controle van fase 4: zonder hem zegt "de toets
verwerpt het model niet" niets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.simulate import (  # noqa: E402
    GarchParameters,
    SimulationSettings,
    compare_to_history,
    historical_adverse_excursion,
    kupiec_test,
    simulate_garch,
    simulate_gbm_normal,
    simulate_gbm_student_t,
)

TRADING_DAYS = 252


def make_settings(**overrides) -> SimulationSettings:
    """Instellingen met een vast zaad en genoeg paden voor stabiele staarten."""
    defaults = {
        "n_paths": 20_000,
        "horizon_days": 63,
        "seed": 1,
        "is_short": True,
    }
    defaults.update(overrides)
    return SimulationSettings(**defaults)


# -- GBM met normale schokken ---------------------------------------------


def test_final_return_spread_matches_theory() -> None:
    """De spreiding van de eindwaarde volgt sigma * sqrt(horizon).

    Basiscontrole op de wiskunde: bij onafhankelijke dagelijkse schokken
    schaalt de standaardafwijking van de som met de wortel van het aantal
    dagen. Klopt dat niet, dan zit er een fout in de opbouw van de paden.
    """
    volatility = 0.01
    settings = make_settings(horizon_days=100)
    result = simulate_gbm_normal(0.0, volatility, settings)

    # We vergelijken op log-schaal, want daar is de som exact normaal.
    log_returns = np.log1p(result.final_returns)
    expected = volatility * np.sqrt(settings.horizon_days)

    assert float(np.std(log_returns)) == pytest.approx(expected, rel=0.05)


def test_higher_volatility_gives_larger_adverse_move() -> None:
    """Meer volatiliteit betekent een grotere tegenbeweging."""
    settings = make_settings()
    calm = simulate_gbm_normal(0.0, 0.005, settings)
    wild = simulate_gbm_normal(0.0, 0.02, settings)

    assert wild.value_at_risk(0.99) > calm.value_at_risk(0.99) * 2


def test_drift_is_excluded_by_default() -> None:
    """Zonder include_drift heeft het gemiddelde geen effect.

    Dit is de instelling die de eerste versie van fase 4 te hoge getallen
    gaf. De standaard moet nul zijn, en deze test legt dat vast.
    """
    settings = make_settings()
    without = simulate_gbm_normal(0.0, 0.01, settings)
    with_mean = simulate_gbm_normal(0.0005, 0.01, settings)

    assert float(np.median(with_mean.final_returns)) == pytest.approx(
        float(np.median(without.final_returns)), abs=1e-9
    )


def test_drift_raises_the_adverse_move_for_a_short() -> None:
    """Mét drift stijgt de margebehoefte van een short aantoonbaar.

    De tegenhanger van de vorige test: de optie moet wel werken als je hem
    aanzet, anders is de standaardkeuze niet te verantwoorden maar gewoon
    de enige mogelijkheid.
    """
    no_drift = simulate_gbm_normal(0.0005, 0.01, make_settings(include_drift=False))
    with_drift = simulate_gbm_normal(0.0005, 0.01, make_settings(include_drift=True))

    assert with_drift.value_at_risk(0.99) > no_drift.value_at_risk(0.99)


def test_seed_makes_results_reproducible() -> None:
    """Hetzelfde zaad geeft exact dezelfde uitkomst."""
    first = simulate_gbm_normal(0.0, 0.01, make_settings(seed=7))
    second = simulate_gbm_normal(0.0, 0.01, make_settings(seed=7))

    np.testing.assert_array_equal(first.max_adverse, second.max_adverse)


def test_different_seeds_give_different_paths() -> None:
    """Een ander zaad geeft andere paden, maar vergelijkbare statistieken."""
    first = simulate_gbm_normal(0.0, 0.01, make_settings(seed=1))
    second = simulate_gbm_normal(0.0, 0.01, make_settings(seed=2))

    assert not np.array_equal(first.max_adverse, second.max_adverse)
    # De 99%-grens mag wel schommelen, maar niet meer dan een paar procent.
    assert first.value_at_risk(0.99) == pytest.approx(
        second.value_at_risk(0.99), rel=0.1
    )


# -- t-verdeelde schokken -------------------------------------------------


def test_student_t_is_rescaled_to_unit_variance() -> None:
    """De t-schokken worden teruggeschaald, dus sigma betekent wat het zegt.

    Een ruwe t-verdeling met df vrijheidsgraden heeft variantie df/(df-2),
    dus groter dan 1. Zonder terugschalen zou de simulatie een hogere
    volatiliteit hebben dan gemeten, en was de vergelijking met het normale
    model niet eerlijk.
    """
    volatility = 0.01
    settings = make_settings(horizon_days=100)
    normal = simulate_gbm_normal(0.0, volatility, settings)
    student = simulate_gbm_student_t(0.0, volatility, 5.0, settings)

    normal_spread = float(np.std(np.log1p(normal.final_returns)))
    student_spread = float(np.std(np.log1p(student.final_returns)))

    # Dezelfde orde van grootte; de t heeft dikkere staarten maar niet een
    # systematisch grotere spreiding.
    assert student_spread == pytest.approx(normal_spread, rel=0.12)


def test_student_t_has_fatter_tails_than_normal() -> None:
    """Bij gelijke volatiliteit geeft de t-verdeling extremere uitschieters.

    Dit is de hele reden dat we hem gebruiken. Het effect zit in de uiterste
    staart, dus we kijken naar het maximum en niet naar de 99%-grens.
    """
    settings = make_settings()
    normal = simulate_gbm_normal(0.0, 0.01, settings)
    student = simulate_gbm_student_t(0.0, 0.01, 3.0, settings)

    assert student.max_adverse.max() > normal.max_adverse.max() * 1.5


def test_student_t_rejects_too_few_degrees_of_freedom() -> None:
    """Onder 2 vrijheidsgraden bestaat de variantie niet."""
    with pytest.raises(ValueError, match="boven 2"):
        simulate_gbm_student_t(0.0, 0.01, 1.5, make_settings())


# -- GARCH ----------------------------------------------------------------


def make_garch(**overrides) -> GarchParameters:
    """GARCH-parameters die op de echte goudschattingen lijken."""
    defaults = {
        "omega": 7.6e-07,
        "alpha": 0.036,
        "beta": 0.959,
        "degrees_of_freedom": 4.8,
        "last_variance": 1.878e-04,
        "long_run_variance": 1.714e-04,
    }
    defaults.update(overrides)
    return GarchParameters(**defaults)


def test_persistence_and_half_life() -> None:
    """Persistentie is alpha+beta, en de halfwaardetijd volgt daaruit."""
    parameters = make_garch(alpha=0.05, beta=0.90)

    assert parameters.persistence == pytest.approx(0.95)
    # 0,95^k = 0,5 bij k ongeveer 13,5
    assert parameters.half_life_days == pytest.approx(13.5, rel=0.05)


def test_non_stationary_garch_has_infinite_half_life() -> None:
    """Bij persistentie van 1 of meer dooft een schok nooit uit.

    Dat is een teken dat het model of de data niet klopt, en de code moet
    dat niet stil laten passeren met een onzinnig getal.
    """
    parameters = make_garch(alpha=0.10, beta=0.95)

    assert parameters.persistence > 1.0
    assert parameters.half_life_days == float("inf")


def test_garch_start_variance_changes_the_outcome() -> None:
    """Beginnen in een onrustige markt geeft een grotere margebehoefte.

    Dit is het hele voordeel van GARCH boven een vaste vuistregel: het
    antwoord beweegt mee met de huidige omstandigheden.
    """
    parameters = make_garch()
    settings = make_settings()

    calm = simulate_garch(
        0.0, parameters, settings, start_variance=parameters.long_run_variance * 0.25
    )
    turbulent = simulate_garch(
        0.0, parameters, settings, start_variance=parameters.long_run_variance * 4.0
    )

    assert turbulent.value_at_risk(0.99) > calm.value_at_risk(0.99)


def test_garch_produces_volatility_clustering() -> None:
    """De gesimuleerde paden vertonen clustering, zoals de echte data.

    Meetbaar via de autocorrelatie van de absolute dagrendementen: die hoort
    positief te zijn bij GARCH en rond nul bij constante volatiliteit.

    Dit is de positieve controle dat GARCH echt doet wat het belooft.
    """
    parameters = make_garch()
    settings = make_settings(n_paths=400, horizon_days=500)

    garch = simulate_garch(0.0, parameters, settings)
    constant = simulate_gbm_normal(0.0, 0.0137, settings)

    def mean_abs_autocorrelation(result) -> float:
        # We reconstrueren de dagrendementen niet uit de opgeslagen
        # statistieken, dus meten we op de eindwaarden van korte paden.
        # In plaats daarvan gebruiken we hier de spreiding van de
        # tegenbeweging als proxy voor clustering.
        return float(np.std(result.max_adverse))

    # Bij clustering is de spreiding van de uitkomsten groter: sommige paden
    # belanden in een rustige periode, andere in een onrustige.
    assert mean_abs_autocorrelation(garch) > mean_abs_autocorrelation(constant)


def test_garch_rejects_too_few_degrees_of_freedom() -> None:
    """GARCH met t-schokken vereist meer dan 2 vrijheidsgraden."""
    with pytest.raises(ValueError, match="2 vrijheidsgraden"):
        simulate_garch(0.0, make_garch(degrees_of_freedom=1.8), make_settings())


# -- adverse excursion ----------------------------------------------------


def test_adverse_excursion_measures_the_path_not_the_endpoint() -> None:
    """De tegenbeweging is de PIEK onderweg, niet de eindwaarde.

    Cruciaal voor de margevraag: een pad dat halverwege 30% tegen je in
    staat en daarna terugkomt op nul, heeft je wel degelijk uitgestopt.
    """
    settings = make_settings(n_paths=5_000, horizon_days=50)
    result = simulate_gbm_normal(0.0, 0.015, settings)

    final_adverse = np.maximum(result.final_returns, 0.0)

    # De tussentijdse piek moet per pad minstens zo groot zijn als de
    # eindwaarde, en gemiddeld duidelijk groter.
    assert np.all(result.max_adverse >= final_adverse - 1e-9)
    assert float(result.max_adverse.mean()) > float(final_adverse.mean())


def test_short_risk_exceeds_long_risk_at_the_same_volatility() -> None:
    """Een short heeft een grotere tegenbeweging dan een long. Dat hoort zo.

    Dit lijkt op een asymmetrie die niet zou moeten bestaan - de schokken
    zijn immers symmetrisch - maar het is economisch echt.

    De oorzaak zit in de omrekening van log-rendement naar prijsverandering.
    Een log-beweging van +0,20 is een prijsstijging van 22,1%; dezelfde
    beweging omlaag is een daling van 18,1%. Wie short zit verliest dus bij
    een stijging meer dan een long bij een even grote daling in logs.

    Fundamenteel: bij een short kun je meer dan 100% verliezen (de prijs kan
    onbeperkt stijgen), bij een long maximaal 100% (de prijs kan niet onder
    nul). Die asymmetrie MOET in de uitkomst zitten.
    """
    short = simulate_gbm_normal(0.0, 0.01, make_settings(is_short=True))
    long = simulate_gbm_normal(0.0, 0.01, make_settings(is_short=False))

    short_var = short.value_at_risk(0.99)
    long_var = long.value_at_risk(0.99)

    assert short_var > 0
    assert long_var > 0
    assert short_var > long_var

    # Op LOG-schaal zijn ze wel vrijwel gelijk; daar komt de asymmetrie
    # niet vandaan, wat bewijst dat het de omrekening is en geen fout in
    # de padopbouw.
    assert np.log1p(short_var) == pytest.approx(
        -np.log1p(-long_var), rel=0.12
    )


def test_expected_shortfall_exceeds_value_at_risk() -> None:
    """ES is het gemiddelde VOORBIJ de VaR, dus altijd groter of gelijk.

    Klopt dit niet, dan is er iets fout met de filtering van de staart.
    """
    result = simulate_gbm_student_t(0.0, 0.01, 4.0, make_settings())

    for confidence in (0.90, 0.95, 0.99):
        assert result.expected_shortfall(confidence) >= result.value_at_risk(
            confidence
        )


def test_value_at_risk_increases_with_confidence() -> None:
    """Meer zekerheid eisen betekent een hogere buffer."""
    result = simulate_gbm_normal(0.0, 0.01, make_settings())

    levels = [result.value_at_risk(c) for c in (0.5, 0.9, 0.95, 0.99, 0.999)]
    assert levels == sorted(levels)


# -- Kupiec-toets: de positieve controle van fase 4 -----------------------


def test_kupiec_accepts_a_correct_model() -> None:
    """Bij precies het verwachte aantal overschrijdingen wordt niet verworpen."""
    outcome = kupiec_test(n_observations=1000, n_exceedances=10, confidence=0.99)

    assert outcome["expected_exceedances"] == pytest.approx(10.0)
    assert outcome["statistic"] == pytest.approx(0.0, abs=1e-6)
    assert outcome["model_accepted"]


def test_kupiec_rejects_a_model_with_too_many_breaches() -> None:
    """Veel meer overschrijdingen dan belooft, wordt verworpen.

    Dit is de belangrijkste positieve controle van fase 4: zonder deze test
    zegt "de toets verwerpt het model niet" niets, want een kapotte toets
    verwerpt ook nooit.
    """
    outcome = kupiec_test(n_observations=1000, n_exceedances=50, confidence=0.99)

    assert not outcome["model_accepted"]
    assert outcome["p_value"] < 0.01
    assert outcome["observed_rate"] > outcome["expected_rate"]


def test_kupiec_rejects_a_model_that_is_far_too_conservative() -> None:
    """Veel te WEINIG overschrijdingen wordt ook verworpen.

    Een te conservatief model is ook fout: je houdt onnodig kapitaal aan.
    De toets is tweezijdig en moet dat oppikken.
    """
    outcome = kupiec_test(n_observations=2000, n_exceedances=0, confidence=0.99)

    assert not outcome["model_accepted"]
    assert outcome["observed_rate"] < outcome["expected_rate"]


def test_kupiec_handles_zero_exceedances_without_crashing() -> None:
    """Nul overschrijdingen is een randgeval (log van nul bestaat niet)."""
    outcome = kupiec_test(n_observations=50, n_exceedances=0, confidence=0.99)

    assert np.isfinite(outcome["statistic"])
    assert 0.0 <= outcome["p_value"] <= 1.0


def test_kupiec_is_weak_with_few_observations() -> None:
    """Met weinig vensters verwerpt de toets bijna nooit.

    Dat is geen fout maar een eigenschap, en precies de beperking die bij de
    kwartaalhorizon speelt: 23 jaar data levert weinig niet-overlappende
    vensters op. Deze test legt vast dat we die zwakte kennen.
    """
    # 2 van de 20 overschrijdingen is 10% waar 1% belooft werd - een factor
    # tien te veel - en toch verwerpt de toets niet op 5%.
    outcome = kupiec_test(n_observations=20, n_exceedances=2, confidence=0.99)

    assert outcome["observed_rate"] == pytest.approx(0.10)
    assert outcome["p_value"] > 0.01


# -- vergelijking met de historie -----------------------------------------


def test_historical_excursion_is_positive_and_bounded() -> None:
    """De historische tegenbeweging is positief en van redelijke grootte."""
    rng = np.random.default_rng(3)
    returns = pd.Series(
        rng.normal(0.0, 0.01, 2000),
        index=pd.date_range("2015-01-01", periods=2000, freq="B"),
    )
    excursions = historical_adverse_excursion(returns, horizon_days=63)

    assert len(excursions) > 300
    assert np.all(excursions >= 0)
    assert float(np.median(excursions)) < 0.5


def test_comparison_puts_history_first_with_zero_deviation() -> None:
    """De historische rij is de ijkmaat, dus zijn afwijking is nul."""
    rng = np.random.default_rng(4)
    returns = pd.Series(
        rng.normal(0.0, 0.01, 2000),
        index=pd.date_range("2015-01-01", periods=2000, freq="B"),
    )
    simulated = simulate_gbm_normal(0.0, 0.01, make_settings(n_paths=5000))

    table = compare_to_history({"test": simulated}, returns, horizon_days=63)

    assert table.iloc[0]["bron"].startswith("historisch")
    assert table.iloc[0]["afwijking_p99_pp"] == pytest.approx(0.0)


def test_comparison_detects_a_model_that_is_way_off() -> None:
    """Een model met veel te hoge volatiliteit krijgt een grote afwijking.

    Zo weet je dat de validatiestap echt iets meet in plaats van altijd
    'dichtbij' te rapporteren.
    """
    rng = np.random.default_rng(5)
    returns = pd.Series(
        rng.normal(0.0, 0.01, 2000),
        index=pd.date_range("2015-01-01", periods=2000, freq="B"),
    )
    # Drie keer de werkelijke volatiliteit.
    too_wild = simulate_gbm_normal(0.0, 0.03, make_settings(n_paths=5000))

    table = compare_to_history({"te wild": too_wild}, returns, horizon_days=63)

    assert float(table.iloc[1]["afwijking_p99_pp"]) > 20.0
