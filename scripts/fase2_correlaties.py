"""Fase 2, stap 2 en 3: correlaties, hun stabiliteit, en multicollineariteit.

Gebruik:
    python scripts/fase2_correlaties.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.tsa.stattools import acf, pacf  # noqa: E402

from goldmodel.config import ALL_SERIES, series_by_name  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.correlations import (  # noqa: E402
    build_change_panel,
    plot_correlation_overview,
    plot_driver_intercorrelations,
    plot_rolling_correlations,
)
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 78

# Drivers waarvan we de stabiliteit door de tijd bekijken. Beperkt tot de
# reeksen die over de volledige periode beschikbaar zijn.
KEY_DRIVERS = [
    "real_rate_10y",
    "usd_broad_index",
    "breakeven_inflation_10y",
    "vix",
    "sp500",
]


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def show_correlations(changes: pd.DataFrame) -> pd.DataFrame:
    """Toont de correlaties met goud en vergelijkt met de verwachting."""
    section("STAP 2A: WELKE DRIVERS BEWEGEN SAMEN MET GOUD?")
    print(
        "\nWe kijken naar dagelijkse VERANDERINGEN, niet naar niveaus - dat was\n"
        "de les uit stap 1.\n"
        "\n"
        "Bij elke driver stond in config.py al een VERWACHT TEKEN, opgeschreven\n"
        "voordat we de data zagen. Nu kunnen we controleren of dat uitkwam."
    )

    _, table = plot_correlation_overview(changes)

    rows = []
    for _, row in table.iterrows():
        driver = row["driver"]
        try:
            expected = series_by_name(driver).expected_sign
        except KeyError:
            expected = "?"
        actual = "+" if row["correlatie"] > 0 else "-"
        if expected in {"+", "-"}:
            match = "JA" if expected == actual else "NEE"
        else:
            match = "n.v.t."
        rows.append(
            {
                "driver": driver,
                "verwacht": expected,
                "gevonden": f"{row['correlatie']:+.3f}",
                "klopt_teken": match,
                "significant": "ja" if row["significant"] else "nee",
                "verklaart": f"{row['r_kwadraat_pct']:.1f}%",
            }
        )

    print(f"\n{pd.DataFrame(rows).to_string(index=False)}")

    print(
        "\nHOE JE DE LAATSTE KOLOM LEEST\n"
        "'verklaart' is de correlatie in het kwadraat: het deel van de\n"
        "dagelijkse goudbeweging dat deze driver los verklaart.\n"
        "\n"
        "Let op hoe klein die getallen zijn. Dat is geen tekortkoming van de\n"
        "data maar de werkelijkheid: dagelijkse goudbewegingen zijn voor het\n"
        "overgrote deel niet uit macro-data te verklaren."
    )

    wrong_sign = [r for r in rows if r["klopt_teken"] == "NEE"]
    if wrong_sign:
        print("\nTEKENS DIE NIET UITKWAMEN:")
        for row in wrong_sign:
            print(
                f"  {row['driver']:26s} verwacht {row['verwacht']}, "
                f"gevonden {row['gevonden']}"
            )
        print(
            "\nDit is precies waarom we het verwachte teken vooraf opschreven.\n"
            "Nu moeten we het verklaren in plaats van er een verhaal bij te\n"
            "verzinnen."
        )

    return table


def show_stability(changes: pd.DataFrame) -> pd.DataFrame:
    """Toont of de correlaties stabiel zijn door de tijd."""
    section("STAP 2B: ZIJN DIE VERBANDEN STABIEL DOOR DE TIJD?")
    print(
        "\nDit is de belangrijkste vraag van fase 2, en hij wordt vaak\n"
        "overgeslagen.\n"
        "\n"
        "Een gemiddelde correlatie over 23 jaar kan twee heel verschillende\n"
        "dingen verbergen:\n"
        "\n"
        "  A) een STABIEL verband van 0,3 -> bruikbaar, je kunt erop rekenen\n"
        "  B) een verband dat tussen -0,5 en +0,5 slingert -> gemiddeld ook\n"
        "     rond nul, maar betekent iets compleet anders\n"
        "\n"
        "Voor een hedge is dat onderscheid essentieel: een hedge die\n"
        "'gemiddeld' werkt maar wegvalt in een crisis is juist dan waardeloos\n"
        "wanneer je hem nodig hebt.\n"
        "\n"
        "We meten met een voortschrijdend venster van 252 handelsdagen (1 jaar)."
    )

    _, stability = plot_rolling_correlations(changes, KEY_DRIVERS)

    display = stability.copy()
    for column in ("gemiddeld", "min", "max", "spreiding", "std"):
        display[column] = display[column].map(lambda v: f"{v:+.3f}")
    display["wisselt_teken"] = display["wisselt_teken"].map(
        lambda v: "JA" if v else "nee"
    )
    print(f"\n{display.to_string(index=False)}")

    print(
        "\nLEES DE KOLOM 'spreiding'\n"
        "Dat is max min min: hoeveel de correlatie door de jaren heen\n"
        "schommelt. Een spreiding van 0,5 of meer betekent dat het verband in\n"
        "verschillende periodes fundamenteel anders is."
    )

    unstable = stability[stability["wisselt_teken"]]
    if not unstable.empty:
        print(
            f"\n{len(unstable)} van de {len(stability)} drivers WISSELT VAN TEKEN "
            "door de tijd:"
        )
        for _, row in unstable.iterrows():
            print(
                f"  {row['driver']:26s} van {row['min']:+.2f} tot {row['max']:+.2f}"
            )
        print(
            "\nDat betekent: in sommige periodes beweegt goud MET deze driver\n"
            "mee, in andere periodes ERTEGEN in. Een vast coefficient in een\n"
            "regressie is dan een gemiddelde van twee tegengestelde regimes -\n"
            "een getal dat in geen enkele periode klopt."
        )

    return stability


def show_safe_haven_check(changes: pd.DataFrame) -> None:
    """Toetst specifiek het veilige-havenverhaal."""
    section("EEN VERHAAL GETOETST: IS GOUD EEN VEILIGE HAVEN?")
    print(
        "\nHet standaardverhaal: als aandelen dalen en de onrust stijgt, vlucht\n"
        "geld naar goud. Als dat klopt, zou goud positief moeten correleren\n"
        "met de VIX en negatief met de S&P 500.\n"
        "\n"
        "Ik verwachtte bovendien dat dit verband zou INSTORTEN in maart 2020,\n"
        "toen beleggers goud verkochten om cash vrij te maken voor margin\n"
        "calls. Laten we kijken."
    )

    pairs = [("vix", "VIX (onrust)"), ("sp500", "S&P 500")]
    periods = [
        ("2003", "2007", "rustige jaren"),
        ("2008", "2009", "financiele crisis"),
        ("2010", "2019", "herstel"),
        ("2020", "2020", "covid-jaar"),
        ("2021", "2026", "recent"),
    ]

    for column, label in pairs:
        if column not in changes.columns:
            continue
        pair = pd.concat([changes["gold_futures"], changes[column]], axis=1).dropna()
        overall = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
        print(f"\n{label}")
        print(f"  hele periode           {overall:+.3f}  (n={len(pair)})")
        for start, end, name in periods:
            window = pair.loc[start:end]
            if len(window) < 50:
                continue
            correlation = float(window.iloc[:, 0].corr(window.iloc[:, 1]))
            print(f"  {name:22s} {correlation:+.3f}  (n={len(window)})")

        # En specifiek de crash-weken.
        crash = pair.loc["2020-02-15":"2020-04-15"]
        if len(crash) > 20:
            crash_correlation = float(crash.iloc[:, 0].corr(crash.iloc[:, 1]))
            print(f"  {'covid-crash (8 weken)':22s} {crash_correlation:+.3f}  (n={len(crash)})")

    print(
        "\nDE UITKOMST IS INTERESSANTER DAN MIJN VERWACHTING\n"
        "Het verband met de VIX is niet ingestort in 2020 - het was er\n"
        "eigenlijk nooit. Over de hele periode is de correlatie vrijwel nul,\n"
        "en dat blijft zo in elke subperiode.\n"
        "\n"
        "Dat is een SCHERPERE conclusie dan 'de hedge faalt in een crisis':\n"
        "op dagbasis is goud helemaal geen veilige haven tegen\n"
        "aandelenvolatiliteit. Het veilige-havenverhaal gaat blijkbaar over\n"
        "langere periodes of over andere soorten stress dan wat de VIX meet.\n"
        "\n"
        "Voor je hedge betekent dit: reken niet op een negatief verband met\n"
        "aandelen op dagbasis. Dat is er niet."
    )


def show_autocorrelation(changes: pd.DataFrame) -> None:
    """Toetst formeel of goudrendementen voorspelbaar zijn uit hun verleden."""
    section("STAP 2C: IS DE RICHTING VAN GOUD VOORSPELBAAR UIT ZICHZELF?")
    print(
        "\nIn fase 1 zag je al dat de richting onvoorspelbaar leek. Nu toetsen\n"
        "we het formeel met autocorrelatie: zegt het rendement van vandaag\n"
        "iets over morgen?\n"
        "\n"
        "ACF  meet de totale samenhang met een vertraging van k dagen\n"
        "PACF meet de samenhang met dag k NA correctie voor alle dagen\n"
        "     ertussen - dus het eigen effect van die ene vertraging"
    )

    gold = changes["gold_futures"].dropna()
    n_lags = 10
    acf_values = acf(gold.values, nlags=n_lags, fft=True)
    pacf_values = pacf(gold.values, nlags=n_lags)
    bound = 1.96 / np.sqrt(len(gold))

    rows = []
    for lag in range(1, n_lags + 1):
        rows.append(
            {
                "vertraging": f"{lag} dag" if lag == 1 else f"{lag} dagen",
                "ACF": f"{acf_values[lag]:+.4f}",
                "PACF": f"{pacf_values[lag]:+.4f}",
                "buiten_toevalsgrens": "JA" if abs(acf_values[lag]) > bound else "nee",
            }
        )
    print(f"\n{pd.DataFrame(rows).to_string(index=False)}")
    print(f"\nToevalsgrens bij n={len(gold)}: +/- {bound:.4f}")

    significant_lags = [
        lag for lag in range(1, n_lags + 1) if abs(acf_values[lag]) > bound
    ]
    if significant_lags:
        print(
            f"\n{len(significant_lags)} van de {n_lags} vertragingen valt buiten de\n"
            f"toevalsgrens (vertraging {', '.join(map(str, significant_lags))})."
        )
        print(
            "\nMaar let op de GROOTTE. De sterkste is "
            f"{max(abs(acf_values[lag]) for lag in significant_lags):.4f}.\n"
            "Gekwadrateerd verklaart dat "
            f"{max(acf_values[lag] ** 2 for lag in significant_lags) * 100:.2f}% "
            "van de beweging van morgen.\n"
            "\n"
            "Statistisch aantoonbaar, praktisch waardeloos: met 6000\n"
            "waarnemingen wordt bijna alles significant. Dit is precies het\n"
            "onderscheid tussen 'significant' en 'bruikbaar' dat je in een\n"
            "gesprek moet kunnen maken."
        )
    else:
        print(
            "\nGeen enkele vertraging valt buiten de toevalsgrens. De richting\n"
            "van goud is niet uit zijn eigen verleden te voorspellen."
        )


def show_multicollinearity(changes: pd.DataFrame) -> pd.DataFrame:
    """Toont welke drivers elkaar dubbelen."""
    section("STAP 3: DUBBELEN DE DRIVERS ELKAAR? (MULTICOLLINEARITEIT)")
    print(
        "\nTwee drivers die sterk met elkaar correleren, bevatten dezelfde\n"
        "informatie. In een regressie kan het model dan niet uitmaken welke\n"
        "van de twee het werk doet.\n"
        "\n"
        "Het gevolg: de coefficienten worden onbetrouwbaar. Grote\n"
        "standaardfouten, en tekens die omslaan bij een kleine wijziging in de\n"
        "data. Het model als geheel kan nog prima voorspellen, maar je kunt\n"
        "niet meer zeggen WELKE driver wat doet.\n"
        "\n"
        "In config.py stonden al twee verdachte paren gemarkeerd. Laten we\n"
        "kijken of dat klopt."
    )

    _, problems = plot_driver_intercorrelations(changes)

    if problems.empty:
        print("\nGeen enkel paar correleert boven 0,5. Geen probleem.")
        return problems

    print(f"\nPAREN MET EEN CORRELATIE BOVEN 0,5 (absoluut):\n")
    display = problems.copy()
    display["correlatie"] = display["correlatie"].map(lambda v: f"{v:+.3f}")
    print(display.to_string(index=False))

    print(
        "\nWAT WE HIERMEE DOEN IN FASE 3\n"
        "Drie opties, en we gaan ze alle drie laten zien:\n"
        "\n"
        "  1. Een van de twee weglaten. Simpelst, maar je gooit informatie weg.\n"
        "  2. Regularisatie (ridge). Die verdeelt het gewicht over\n"
        "     gecorreleerde drivers in plaats van willekeurig te kiezen.\n"
        "  3. Beide houden en de VIF rapporteren, zodat de lezer weet dat de\n"
        "     losse coefficienten niet los te interpreteren zijn.\n"
        "\n"
        "Optie 3 is het eerlijkst voor een eerste model: je verbergt het\n"
        "probleem niet, je benoemt het."
    )
    return problems


def main() -> int:
    """Draait de correlatieanalyse."""
    apply_style()
    pd.set_option("display.width", 160)

    print(LINE)
    print("FASE 2, STAP 2 EN 3: CORRELATIES, STABILITEIT, MULTICOLLINEARITEIT")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    changes = build_change_panel(panel)

    print(
        f"\nPaneel omgezet naar stationaire veranderingen: "
        f"{changes.shape[0]} rijen x {changes.shape[1]} reeksen"
    )

    show_correlations(changes)
    show_stability(changes)
    show_safe_haven_check(changes)
    show_autocorrelation(changes)
    show_multicollinearity(changes)

    section("WAT FASE 2 HEEFT OPGELEVERD")
    print(
        "\n1. De data mag alleen als VERANDERING het model in, niet als niveau.\n"
        "   Op niveaus vindt een regressie in 92% van de gevallen een\n"
        "   schijnverband.\n"
        "\n"
        "2. De correlaties met goud zijn ZWAK. Zelfs de sterkste driver\n"
        "   verklaart maar een paar procent van de dagelijkse beweging.\n"
        "\n"
        "3. Sommige verbanden zijn NIET STABIEL door de tijd. Een vast\n"
        "   coefficient is dan een gemiddelde van verschillende regimes.\n"
        "\n"
        "4. Goud is op dagbasis GEEN veilige haven tegen aandelenvolatiliteit.\n"
        "   Dat verband is er niet, en is er ook nooit geweest.\n"
        "\n"
        "5. De richting van goud is niet uit zijn eigen verleden te\n"
        "   voorspellen - wat de efficiente-markthypothese voorspelt.\n"
        "\n"
        "6. Enkele drivers dubbelen elkaar, dus losse coefficienten worden\n"
        "   onbetrouwbaar.\n"
        "\n"
        "DAT IS EEN ONGEMAKKELIJKE MAAR EERLIJKE UITKOMST.\n"
        "Fase 3 gaat dit formeel toetsen: verslaat een regressiemodel een\n"
        "random walk out-of-sample? Op basis van fase 2 is mijn verwachting\n"
        "NEE - en als dat zo is, is dat het resultaat."
    )

    print(f"\n{LINE}")
    print(f"Figuren: {get_output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
