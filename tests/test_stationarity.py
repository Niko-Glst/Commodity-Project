"""Tests voor de stationariteitstoetsen.

De belangrijkste tests hier zijn de POSITIEVE CONTROLES: geef de toetsen data
waarvan we het antwoord vooraf kennen, en controleer dat ze dat antwoord
geven. Zonder die controle betekent "niet stationair" niets, want een kapotte
toets zegt dat ook.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from goldmodel.viz.stationarity import (  # noqa: E402
    generate_independent_walks,
    run_stationarity_tests,
    spurious_regression_rate,
)


# -- positieve controles: kennen we het antwoord, vindt de toets het? ------


def test_white_noise_is_stationair() -> None:
    """Zuivere ruis is stationair; ADF hoort dat altijd te zien.

    We toetsen hier alleen op ADF, want KPSS geeft op ruis af en toe een
    valse verwerping — zie ``test_kpss_gives_occasional_false_alarms``. Dat
    is een bekende eigenschap van de toets, geen fout in deze code.
    """
    rng = np.random.default_rng(2)
    noise = pd.Series(rng.standard_normal(2000))

    outcome = run_stationarity_tests(noise, name="ruis")

    assert outcome["adf_rejects"] is True
    assert outcome["adf_p"] < 0.01
    assert outcome["verdict"] == "stationair"


def test_kpss_gives_occasional_false_alarms_on_pure_noise() -> None:
    """KPSS verwerpt soms stationariteit op data die per constructie ruis is.

    Dit legt een eigenschap van de toets vast die je moet kennen bij het
    interpreteren van de resultaten: een enkele KPSS-verwerping is geen hard
    bewijs van niet-stationariteit. Daarom kijken we altijd naar BEIDE
    toetsen, en is 'onduidelijk' een geldige uitkomst in plaats van iets dat
    we wegpoetsen.

    Bij 40 reeksen zuivere ruis verwachten we bij een grens van 5% ongeveer
    2 valse verwerpingen; in de praktijk zijn het er meer, omdat de
    asymptotische verdeling van KPSS in eindige steekproeven niet exact
    klopt.
    """
    false_alarms = 0
    for seed in range(40):
        rng = np.random.default_rng(seed)
        outcome = run_stationarity_tests(pd.Series(rng.standard_normal(1500)))
        if outcome["kpss_rejects"]:
            false_alarms += 1

    # Het punt is dat het er MEER dan nul zijn, en toch een minderheid.
    assert 0 < false_alarms < 20, (
        f"{false_alarms}/40 valse verwerpingen; verwacht een klein aantal"
    )


def test_random_walk_is_not_stationair() -> None:
    """Een random walk is per definitie niet stationair."""
    rng = np.random.default_rng(2)
    walk = pd.Series(np.cumsum(rng.standard_normal(2000)))

    outcome = run_stationarity_tests(walk, name="random walk")

    assert outcome["verdict"] == "NIET stationair"
    assert outcome["adf_rejects"] is False
    assert outcome["kpss_rejects"] is True


def test_differencing_a_random_walk_makes_it_stationair() -> None:
    """Het eerste verschil van een random walk is ruis, dus stationair.

    Dit is precies de transformatie die we op de prijsreeksen toepassen.
    """
    rng = np.random.default_rng(3)
    walk = pd.Series(np.cumsum(rng.standard_normal(2000)))

    before = run_stationarity_tests(walk)
    after = run_stationarity_tests(walk.diff().dropna())

    assert before["verdict"] == "NIET stationair"
    assert after["verdict"] == "stationair"


def test_mean_reverting_series_is_stationair() -> None:
    """Een AR(1) met phi ruim onder 1 keert terug naar zijn gemiddelde."""
    rng = np.random.default_rng(4)
    n = 2000
    values = np.empty(n)
    values[0] = 0.0
    for i in range(1, n):
        values[i] = 0.7 * values[i - 1] + rng.standard_normal()

    outcome = run_stationarity_tests(pd.Series(values), name="AR(1)")

    assert outcome["verdict"] == "stationair"


def test_series_with_trend_is_flagged() -> None:
    """Een reeks met een duidelijke trend is niet stationair rond een constante.

    We toetsen met ``regression="c"``, dus tegen een constante. Een reeks met
    een deterministische trend hoort dan verworpen te worden — niet omdat hij
    onvoorspelbaar is, maar omdat zijn gemiddelde wegloopt.
    """
    rng = np.random.default_rng(5)
    n = 1500
    trending = pd.Series(np.arange(n) * 0.05 + rng.standard_normal(n))

    outcome = run_stationarity_tests(trending, name="trend")

    assert outcome["kpss_rejects"] is True
    assert outcome["verdict"] != "stationair"


# -- de twee toetsen vullen elkaar aan -------------------------------------


def test_verdict_labels_cover_all_four_combinations() -> None:
    """Elke combinatie van ADF en KPSS krijgt een begrijpelijk oordeel."""
    rng = np.random.default_rng(6)
    cases = [
        pd.Series(rng.standard_normal(1500)),
        pd.Series(np.cumsum(rng.standard_normal(1500))),
        pd.Series(np.arange(1500) * 0.03 + rng.standard_normal(1500)),
    ]
    verdicts = {run_stationarity_tests(c)["verdict"] for c in cases}

    allowed = {"stationair", "NIET stationair", "onduidelijk"}
    assert verdicts <= allowed
    # Elk oordeel gaat gepaard met een uitleg.
    for case in cases:
        assert run_stationarity_tests(case)["explanation"]


def test_test_output_contains_critical_values() -> None:
    """De kritieke waarden worden meegegeven, niet alleen de p-waarde.

    Bij een p-waarde die tegen de tabelgrens aanloopt (KPSS rapporteert
    bijvoorbeeld 0,1 als bovengrens) is de toetsingsgrootheid naast de
    kritieke waarde informatiever dan de afgekapte p-waarde.
    """
    rng = np.random.default_rng(7)
    outcome = run_stationarity_tests(pd.Series(rng.standard_normal(1000)))

    assert "adf_critical_5pct" in outcome
    assert "kpss_critical_5pct" in outcome
    assert outcome["adf_statistic"] < outcome["adf_critical_5pct"]


# -- schijnregressie -------------------------------------------------------


def test_independent_walks_really_are_independent() -> None:
    """De gegenereerde reeksen hebben geen verband in hun veranderingen.

    Controle op de opzet van het experiment: als de reeksen per ongeluk wel
    samenhingen, zou de demonstratie niets bewijzen.
    """
    a, b = generate_independent_walks(3000, seed=11)

    correlation_of_changes = a.diff().corr(b.diff())

    assert abs(correlation_of_changes) < 0.06


def test_levels_regression_finds_far_too_many_false_positives() -> None:
    """Op niveaus is het foutenpercentage veel hoger dan de beloofde 5%.

    Dit is de kern van fase 2, vastgelegd als test: de toets is kapot op
    niet-stationaire data.
    """
    rates = spurious_regression_rate(n_simulations=200, n_observations=400, seed=13)

    # Gemeten rond 90%; we toetsen ruim onder die waarde zodat de test niet
    # op toevallige variatie faalt.
    assert rates["levels_false_positive_rate"] > 0.5
    # En de R2 ziet eruit als een goed model, terwijl er niets te verklaren is.
    assert rates["median_r_squared_levels"] > 0.1


def test_differences_regression_has_correct_false_positive_rate() -> None:
    """Op veranderingen klopt het foutenpercentage wel ongeveer.

    Bij een significantieniveau van 5% hoort een toets in ongeveer 5% van de
    gevallen ten onrechte 'significant' te zeggen. We staan een ruime marge
    toe omdat 200 simulaties zelf steekproefruis hebben.
    """
    rates = spurious_regression_rate(n_simulations=200, n_observations=400, seed=17)

    assert rates["diffs_false_positive_rate"] < 0.12


def test_spurious_rate_is_much_worse_on_levels() -> None:
    """Het verschil tussen de twee is groot, niet marginaal."""
    rates = spurious_regression_rate(n_simulations=200, n_observations=400, seed=19)

    assert rates["levels_false_positive_rate"] > rates["diffs_false_positive_rate"] * 5
