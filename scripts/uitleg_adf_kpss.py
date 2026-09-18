"""Legt ADF en KPSS uit vanaf nul, met zo weinig statistiek als mogelijk.

Gebruik:
    python scripts/uitleg_adf_kpss.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.basics import (  # noqa: E402
    plot_what_the_tests_do,
    plot_why_two_series_is_different,
)
from goldmodel.viz.stationarity import run_stationarity_tests  # noqa: E402
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 76


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def where_we_are() -> None:
    """Zet de overgang van fase 1 naar fase 2 neer."""
    section("EERST: WAT VERANDERT ER TUSSEN FASE 1 EN FASE 2?")
    print(
        "\nFASE 1 KEEK NAAR EEN REEKS: GOUD.\n"
        "  Je weet nu:\n"
        "    - dalingen zijn extremer dan stijgingen (scheefheid -0,53)\n"
        "    - 4- en 5-sigma dagen komen veel vaker voor dan de klokvorm zegt\n"
        "      (kurtosis 6,5), dus een t-verdeling past beter\n"
        "    - volatiliteit clustert: onrustige dag vandaag = grote kans op\n"
        "      onrustige dag morgen\n"
        "    - maar zonder vast ritme, dus je kunt er geen timing op zetten\n"
        "\n"
        "Dat is compleet. Daar hoeft niets bij.\n"
        "\n"
        "FASE 2 KIJKT NAAR TWEE REEKSEN TEGELIJK.\n"
        "  De nieuwe vraag: beweegt goud MEE met de rente? Met de dollar?\n"
        "\n"
        "En daar komt een probleem bij kijken dat bij EEN reeks niet bestaat.\n"
        "Dat probleem is de reden dat ADF en KPSS er zijn."
    )


def the_problem() -> None:
    """Toont het probleem met een niet-financieel voorbeeld."""
    section("HET PROBLEEM, MET EEN VOORBEELD BUITEN DE FINANCIELE WERELD")

    years = np.arange(2003, 2027)
    population = 16.2 + (years - 2003) * 0.08
    subscribers = 1.5 + (years - 2003) * 12.0

    print("\nTwee dingen die allebei zijn gegroeid sinds 2003:\n")
    print(f"  {'jaar':6s} {'NL bevolking (mln)':>20s} {'Netflix (mln)':>15s}")
    print(f"  {'-' * 6} {'-' * 20} {'-' * 15}")
    for year, pop, subs in list(zip(years, population, subscribers))[::6]:
        print(f"  {year:6d} {pop:>20.1f} {subs:>15.1f}")

    correlation = float(pd.Series(population).corr(pd.Series(subscribers)))
    print(f"\n  Correlatie tussen deze twee: {correlation:+.3f}")

    print(
        "\nEen correlatie van +1,00 is perfect. Volgens de statistiek is dit\n"
        "het sterkst mogelijke verband dat bestaat.\n"
        "\n"
        "Groeit Netflix DOOR de Nederlandse bevolking? Natuurlijk niet.\n"
        "\n"
        "WAT ER MISGAAT\n"
        "De twee delen maar een ding: DE TIJD. Beide gaan omhoog naarmate de\n"
        "jaren verstrijken. Een correlatie meet 'bewegen ze samen', en het\n"
        "antwoord is ja - maar niet omdat de een de ander beweegt.\n"
        "\n"
        "Dit heet een SCHIJNVERBAND. En het is geen randgeval: bij twee reeksen\n"
        "die allebei een trend hebben, gebeurt dit vrijwel ALTIJD."
    )


def why_gold_has_this_problem(panel: pd.DataFrame) -> None:
    """Laat zien dat goud en de rente hetzelfde probleem hebben."""
    section("WAAROM DIT BIJ GOUD OOK SPEELT")

    gold = panel["gold_futures"].dropna()
    print(
        f"\nDe goudprijs ging van ${gold.iloc[0]:,.0f} in "
        f"{gold.index[0].year} naar ${gold.iloc[-1]:,.0f} nu.\n"
        "Dat is een trend van 23 jaar omhoog.\n"
        "\n"
        "Elke andere reeks die in die periode ook omhoog ging, correleert\n"
        "daarmee. Ongeacht of er een verband is.\n"
        "\n"
        "Dus als ik de goudprijs tegen de rente zet en een sterk verband vind,\n"
        "weet ik niet of dat komt doordat:\n"
        "\n"
        "  A) goud echt reageert op de rente, OF\n"
        "  B) ze in dezelfde periode toevallig dezelfde kant op liepen\n"
        "\n"
        "Dat onderscheid MOET ik kunnen maken, anders is mijn hele fase 3\n"
        "waardeloos."
    )


def the_solution() -> None:
    """Legt de oplossing uit."""
    section("DE OPLOSSING: KIJK NAAR DE VERANDERINGEN")
    print(
        "\nIn plaats van: 'de goudprijs is $4.343 en de rente is 2,6%'\n"
        "kijk je naar:   'goud ging vandaag +0,8% en de rente +0,03 punt'\n"
        "\n"
        "Waarom dat werkt: een trend zit in de NIVEAUS, niet in de dagelijkse\n"
        "VERANDERINGEN. De goudprijs loopt 23 jaar omhoog, maar de dagelijkse\n"
        "verandering schommelt rond nul - vandaag omhoog, morgen omlaag.\n"
        "\n"
        "Door naar veranderingen te kijken haal je de trend eruit. Wat\n"
        "overblijft is: bewegen ze op DEZELFDE DAGEN dezelfde kant op? En dat\n"
        "is de vraag die je eigenlijk wilde stellen.\n"
        "\n"
        "EN DIT IS WAT JE AL WIST\n"
        "In fase 1 heb je nooit met prijzen gerekend, altijd met RENDEMENTEN.\n"
        "Dat is precies dezelfde stap. Je deed het al goed; nu weet je waarom."
    )


def what_the_tests_are(panel: pd.DataFrame) -> None:
    """Legt uit wat ADF en KPSS zijn."""
    section("WAT ZIJN ADF EN KPSS DAN?")
    print(
        "\nHet zijn twee toetsen die EEN vraag beantwoorden:\n"
        "\n"
        "   'Heeft deze reeks een vast niveau waar hij naar terugkeert,\n"
        "    of loopt hij weg?'\n"
        "\n"
        "Het vakwoord voor 'heeft een vast niveau' is STATIONAIR.\n"
        "\n"
        "  STATIONAIR         het gemiddelde is hetzelfde in 2005 en in 2025\n"
        "                     -> veilig om te regresseren\n"
        "\n"
        "  NIET STATIONAIR    het gemiddelde loopt weg over tijd\n"
        "                     -> gevaar voor schijnverbanden\n"
        "\n"
        "Dat is alles. De toetsen zijn een formele check op iets dat je vaak\n"
        "ook gewoon kunt zien."
    )

    gold = panel["gold_futures"].dropna()
    returns = np.log(gold / gold.shift(1)).dropna() * 100

    early_price = gold.loc[:"2008"].mean()
    late_price = gold.loc["2021":].mean()
    early_ret = returns.loc[:"2008"].mean()
    late_ret = returns.loc["2021":].mean()

    print("\nKIJK ZELF, ZONDER TOETS:\n")
    print(f"  {'':28s} {'2003-2008':>14s} {'2021-2026':>14s}")
    print(f"  {'-' * 28} {'-' * 14} {'-' * 14}")
    print(f"  {'Gemiddelde GOUDPRIJS':28s} {early_price:>13,.0f}$ {late_price:>13,.0f}$")
    print(f"  {'Gemiddeld DAGRENDEMENT':28s} {early_ret:>13.3f}% {late_ret:>13.3f}%")
    print(
        f"\n  De prijs: {late_price / early_price:.1f} keer zo hoog. Weggelopen.\n"
        f"  Het rendement: verschil van {abs(late_ret - early_ret):.3f} procentpunt. "
        "Vrijwel gelijk.\n"
        "\n"
        "Daar heb je geen toets voor nodig. De toets geeft er een getal bij,\n"
        "zodat je het kunt opschrijven in plaats van 'het lijkt me wel'."
    )


def how_to_read_them(panel: pd.DataFrame) -> None:
    """Legt uit hoe je de uitkomst leest."""
    section("HOE JE DE UITKOMST LEEST")
    print(
        "\nHier zit de verwarring, en het is echt verwarrend: de twee toetsen\n"
        "stellen de vraag PRECIES OMGEKEERD.\n"
        "\n"
        "ADF  begint met aannemen: 'deze reeks is NIET stationair'\n"
        "     en kijkt of de data dat tegenspreekt.\n"
        "     -> kleine p-waarde = de data spreekt het tegen\n"
        "                        = de reeks IS dus stationair\n"
        "\n"
        "KPSS begint met aannemen: 'deze reeks IS stationair'\n"
        "     en kijkt of de data dat tegenspreekt.\n"
        "     -> kleine p-waarde = de data spreekt het tegen\n"
        "                        = de reeks is dus NIET stationair\n"
        "\n"
        "Dus dezelfde kleine p-waarde betekent bij de twee toetsen het\n"
        "TEGENOVERGESTELDE. Dat is de enige moeilijkheid; de rest is simpel.\n"
        "\n"
        "TRUCJE OM HET TE ONTHOUDEN\n"
        "  Een kleine p-waarde betekent altijd: 'de aanname was fout'.\n"
        "  Je moet dus alleen weten met welke aanname elke toets begint.\n"
        "  ADF begint pessimistisch (niet stationair),\n"
        "  KPSS begint optimistisch (wel stationair).\n"
        "\n"
        "WAAROM TWEE TOETSEN DIE ELKAARS TEGENPOOL ZIJN?\n"
        "Omdat ze elkaar dan kunnen controleren. Zeggen ze hetzelfde, dan ben\n"
        "je zeker. Spreken ze elkaar tegen, dan is er iets bijzonders aan de\n"
        "hand - en dan wil je dat weten in plaats van een getal geloven."
    )

    print("\nOP JOUW EIGEN DATA:\n")
    gold = panel["gold_futures"].dropna()
    returns = np.log(gold / gold.shift(1)).dropna()

    for series, label in ((gold, "goudPRIJS"), (returns, "goudRENDEMENT")):
        outcome = run_stationarity_tests(series)
        adf_says = "wel stationair" if outcome["adf_rejects"] else "niet stationair"
        kpss_says = "niet stationair" if outcome["kpss_rejects"] else "wel stationair"
        print(f"  {label}")
        print(f"    ADF  p = {outcome['adf_p']:.3f}  -> zegt: {adf_says}")
        print(f"    KPSS p = {outcome['kpss_p']:.3f}  -> zegt: {kpss_says}")
        print(f"    Beide eens? {'JA' if adf_says == kpss_says else 'nee'}"
              f"  -> conclusie: {outcome['verdict']}\n")

    print(
        "Precies wat je al zag zonder toets: de prijs loopt weg, het rendement\n"
        "niet."
    )


def what_this_changes() -> None:
    """Sluit af met wat dit praktisch betekent."""
    section("WAT DIT VERANDERT AAN HET PROJECT")
    print(
        "\nEigenlijk: niets. En dat is het punt.\n"
        "\n"
        "Je werkte in fase 1 al met rendementen in plaats van prijzen. Dat was\n"
        "toevallig ook precies goed. De toetsen bevestigen dat, en nu kun je\n"
        "uitleggen WAAROM het goed was.\n"
        "\n"
        "Wat het wel verandert: je hebt nu een antwoord op een interviewvraag\n"
        "die zeker komt.\n"
        "\n"
        "  Vraag:   'Waarom heb je met rendementen gerekend en niet met prijzen?'\n"
        "\n"
        "  Antwoord: 'Omdat prijsreeksen niet-stationair zijn - getoetst met ADF\n"
        "            en KPSS, tien van mijn twaalf reeksen. Op niet-stationaire\n"
        "            data vindt een regressie schijnverbanden: ik heb het\n"
        "            gemeten met toevalsreeksen en kreeg in 92% van de gevallen\n"
        "            een significant verband waar er geen was.'\n"
        "\n"
        "Dat is een compleet, verdedigbaar antwoord. Dat is wat fase 2 stap 1\n"
        "je heeft opgeleverd."
    )


def main() -> int:
    """Draait de uitleg."""
    apply_style()
    pd.set_option("display.width", 140)

    print(LINE)
    print("ADF EN KPSS, VANAF NUL")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)

    where_we_are()
    the_problem()
    why_gold_has_this_problem(panel)
    the_solution()
    what_the_tests_are(panel)
    how_to_read_them(panel)
    what_this_changes()

    print(f"\n{LINE}\nFIGUREN\n{LINE}")
    plot_why_two_series_is_different()
    plot_what_the_tests_do(panel)
    print(f"\nStaan in: {get_output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
