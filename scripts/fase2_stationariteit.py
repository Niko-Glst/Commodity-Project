"""Fase 2, stap 1: stationariteit toetsen.

De vraag die dit beantwoordt: in welke VORM mogen de reeksen het model in?

Gebruik:
    python scripts/fase2_stationariteit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldmodel.config import ALL_SERIES, series_by_name  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.stationarity import (  # noqa: E402
    plot_spurious_regression,
    plot_stationarity_comparison,
    run_stationarity_tests,
)
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 78


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def explain_the_problem() -> None:
    """Legt uit waarom stationariteit de eerste vraag is."""
    section("WAAROM DIT DE EERSTE VRAAG IS")
    print(
        "\nFase 1 vroeg: HOE beweegt goud? (dikke staarten, scheefheid,\n"
        "volatiliteitsclustering)\n"
        "\n"
        "Fase 2 vraagt: WAAROM beweegt goud? Kunnen we het verklaren uit de\n"
        "rente, de dollar, de inflatieverwachting?\n"
        "\n"
        "Maar daar zit een valkuil tussen, en die moeten we eerst wegnemen.\n"
        "\n"
        "DE VALKUIL\n"
        "Regresseer je twee reeksen die allebei een trend hebben, dan vind je\n"
        "vrijwel altijd een sterk, 'significant' verband - ook als de reeksen\n"
        "niets met elkaar te maken hebben.\n"
        "\n"
        "De oorzaak in een zin: twee reeksen die allebei omhoog lopen over\n"
        "tijd, bewegen samen. De regressie ziet gezamenlijke BEWEGING en\n"
        "noemt dat gezamenlijke OORZAAK.\n"
        "\n"
        "Dit heet SCHIJNREGRESSIE (spurious regression), beschreven door\n"
        "Granger en Newbold in 1974. Het is de meest voorkomende manier\n"
        "waarop econometrisch onderzoek fout gaat."
    )


def demonstrate_spurious() -> None:
    """Toont schijnregressie met verzonnen data."""
    section("BEWIJS: TWEE REEKSEN DIE NIETS MET ELKAAR TE MAKEN HEBBEN")
    print(
        "\nIk maak twee reeksen met een toevalsgenerator. Elke reeks is een\n"
        "cumulatieve som van eigen toevalsgetallen - er is per constructie\n"
        "GEEN verband. Geen gedeelde schok, geen gedeelde trend, niets.\n"
        "\n"
        "Elk verband dat een regressie hier vindt, is dus per definitie schijn."
    )

    _, rates = plot_spurious_regression()

    print(
        f"\nResultaat van {rates['n_simulations']} herhalingen met steeds nieuwe\n"
        "toevalsreeksen:\n"
    )
    print(
        f"  Regressie op NIVEAUS       'significant' in "
        f"{rates['levels_false_positive_rate']:.0%} van de gevallen"
    )
    print(
        f"  Regressie op VERANDERINGEN 'significant' in "
        f"{rates['diffs_false_positive_rate']:.0%} van de gevallen"
    )
    print(f"\n  Mediane R2 op niveaus: {rates['median_r_squared_levels']:.2f}")
    print(
        "\nLees dat goed. Bij een significantieniveau van 5% HOORT een toets\n"
        "5% van de tijd ten onrechte 'significant' te zeggen. Op veranderingen\n"
        "klopt dat ongeveer. Op niveaus is het veel hoger: de toets is dan\n"
        "gewoon kapot.\n"
        "\n"
        "En die mediane R2 is het gevaarlijkst: dat getal ziet eruit als een\n"
        "goed model, terwijl er niets te verklaren valt."
    )


def explain_stationarity() -> None:
    """Legt het begrip stationariteit uit."""
    section("DE OPLOSSING: STATIONARITEIT")
    print(
        "\nEen reeks is STATIONAIR als zijn statistische eigenschappen niet van\n"
        "de tijd afhangen:\n"
        "\n"
        "  - hetzelfde gemiddelde, of je naar 2005 of 2025 kijkt\n"
        "  - dezelfde spreiding\n"
        "  - dezelfde samenhang met zijn eigen verleden\n"
        "\n"
        "Een prijsreeks is dat vrijwel nooit. Goud stond rond $400 in 2003 en\n"
        "rond $4.300 in 2026. Er is geen 'gemiddelde goudprijs' waar hij naar\n"
        "terugkeert - het gemiddelde hangt af van welke periode je pakt.\n"
        "\n"
        "Rendementen zijn dat meestal wel: het gemiddelde dagrendement is\n"
        "ongeveer 0,04%, en dat blijft zo in elke periode.\n"
        "\n"
        "DAAROM WERKEN WE MET RENDEMENTEN.\n"
        "Niet omdat het gebruikelijk is, maar omdat de alternatieve\n"
        "berekening kapot is."
    )


def test_all_series(panel: pd.DataFrame) -> pd.DataFrame:
    """Toetst elke reeks in niveau en in eerste verschil."""
    section("DE TOETSEN OP JOUW EIGEN DATA")
    print(
        "\nTwee toetsen, met TEGENGESTELDE nulhypotheses:\n"
        "\n"
        "  ADF   nulhypothese: de reeks is NIET stationair\n"
        "        -> kleine p-waarde = bewijs VOOR stationariteit\n"
        "\n"
        "  KPSS  nulhypothese: de reeks IS stationair\n"
        "        -> kleine p-waarde = bewijs TEGEN stationariteit\n"
        "\n"
        "Waarom twee toetsen met omgekeerde vraagstelling? Omdat ze elkaar dan\n"
        "kunnen bevestigen of tegenspreken. Zeggen ze hetzelfde, dan ben je\n"
        "zeker. Spreken ze elkaar tegen, dan is je reeks ingewikkelder dan\n"
        "'wel of niet stationair' - bijvoorbeeld door een structuurbreuk.\n"
        "\n"
        "Een toets kan namelijk ook falen door te weinig data. Twee toetsen\n"
        "die onafhankelijk hetzelfde zeggen, is veel sterker bewijs."
    )

    rows = []
    for column in panel.columns:
        series = panel[column].dropna()
        if len(series) < 200:
            continue

        level = run_stationarity_tests(series, name=column)

        # Voor prijsreeksen het log-rendement, voor rentes het eerste verschil.
        try:
            spec = series_by_name(column)
            use_log_return = "rendement" in spec.transform_hint
        except KeyError:
            use_log_return = False

        if use_log_return and (series > 0).all():
            transformed = np.log(series / series.shift(1)).dropna()
            transform_label = "log-rendement"
        else:
            transformed = series.diff().dropna()
            transform_label = "eerste verschil"

        diff = run_stationarity_tests(transformed, name=f"d.{column}")

        rows.append(
            {
                "reeks": column,
                "niveau_adf_p": level["adf_p"],
                "niveau_kpss_p": level["kpss_p"],
                "niveau": level["verdict"],
                "transformatie": transform_label,
                "na_adf_p": diff["adf_p"],
                "na_kpss_p": diff["kpss_p"],
                "na_transformatie": diff["verdict"],
            }
        )

    frame = pd.DataFrame(rows)

    display = frame.copy()
    for column in ("niveau_adf_p", "niveau_kpss_p", "na_adf_p", "na_kpss_p"):
        display[column] = display[column].map(lambda v: f"{v:.3f}")

    print("\nRESULTATEN\n")
    print(
        display[
            ["reeks", "niveau_adf_p", "niveau_kpss_p", "niveau"]
        ].to_string(index=False)
    )

    print("\nNA TRANSFORMATIE\n")
    print(
        display[
            ["reeks", "transformatie", "na_adf_p", "na_kpss_p", "na_transformatie"]
        ].to_string(index=False)
    )

    return frame


def interpret(frame: pd.DataFrame) -> None:
    """Vat samen wat de toetsen betekenen voor het model."""
    section("WAT DIT BETEKENT VOOR HET MODEL")

    non_stationary_levels = (frame["niveau"] == "NIET stationair").sum()
    stationary_levels = (frame["niveau"] == "stationair").sum()
    unclear_levels = (frame["niveau"] == "onduidelijk").sum()
    stationary_after = (frame["na_transformatie"] == "stationair").sum()

    print(
        f"\nOp NIVEAU:\n"
        f"  niet stationair : {non_stationary_levels} van {len(frame)}\n"
        f"  stationair      : {stationary_levels}\n"
        f"  onduidelijk     : {unclear_levels}\n"
        f"\nNA TRANSFORMATIE:\n"
        f"  stationair      : {stationary_after} van {len(frame)}"
    )

    still_problematic = frame[frame["na_transformatie"] != "stationair"]
    if not still_problematic.empty:
        print("\nREEKSEN DIE OOK NA TRANSFORMATIE NIET SCHOON ZIJN:")
        for _, row in still_problematic.iterrows():
            print(
                f"  {row['reeks']:26s} ADF p={row['na_adf_p']:.3f}  "
                f"KPSS p={row['na_kpss_p']:.3f}  -> {row['na_transformatie']}"
            )
        print(
            "\nDat is geen reden om ze weg te gooien, maar wel om er bij de\n"
            "interpretatie rekening mee te houden. Ik kom er in fase 3 op terug."
        )

    print(
        "\nDE CONCLUSIE\n"
        "De prijsniveaus mogen NIET rechtstreeks in een regressie. Alles gaat\n"
        "als rendement of als eerste verschil het model in.\n"
        "\n"
        "Dat heeft een prijs die je moet kennen: door te differentieren gooi\n"
        "je informatie over het NIVEAU weg. Een verband als 'goud is duur ten\n"
        "opzichte van de reele rente' kun je in verschillen niet meer zien.\n"
        "\n"
        "Er bestaat een techniek die dat wel kan (cointegratie), en die is\n"
        "inhoudelijk interessant voor goud en de reele rente. Dat is een\n"
        "mogelijke uitbreiding, geen onderdeel van het basismodel."
    )


def main() -> int:
    """Draait de stationariteitsanalyse."""
    apply_style()
    pd.set_option("display.width", 150)

    print(LINE)
    print("FASE 2, STAP 1: IN WELKE VORM MAG DE DATA HET MODEL IN?")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    print(f"\nPaneel: {panel.shape[0]} rijen x {panel.shape[1]} reeksen")

    explain_the_problem()
    demonstrate_spurious()
    explain_stationarity()

    print("\nFiguur met de goudprijs naast de goudrendementen:")
    plot_stationarity_comparison(panel)

    frame = test_all_series(panel)
    interpret(frame)

    print(f"\n{LINE}")
    print(f"Figuren: {get_output_dir()}")
    print(
        "\nVOLGENDE STAP (fase 2, stap 2)\n"
        "Nu we weten in welke vorm de data het model in mag, kunnen we naar de\n"
        "verbanden kijken: correlaties tussen de drivers, en of die verbanden\n"
        "stabiel zijn door de tijd. Dat laatste is waar het interessant wordt -\n"
        "ik verwacht dat de veilige-havenrelatie met de VIX instort in 2020."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
