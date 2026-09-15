"""Legt de margemechaniek uit met een echt voorbeeld, dag voor dag.

Gebruikt september 2008 (de week na Lehman Brothers) omdat dat de zwaarste
periode voor een short goudpositie in de hele reeks is.

Gebruik:
    python scripts/uitleg_marge.py
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
from goldmodel.margin import (  # noqa: E402
    CONTRACT_SIZE_OUNCES,
    MarginSettings,
    buffer_needed_for_confidence,
    simulate_margin,
)
from goldmodel.viz.distributions import compute_returns  # noqa: E402

LINE = "=" * 78


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def explain_basics(spot: float) -> None:
    """Legt de begrippen uit met de actuele goudprijs."""
    section("DEEL 1: WAT JE EIGENLIJK KOOPT")

    notional = spot * CONTRACT_SIZE_OUNCES
    initial = notional * 0.05

    print(
        f"\nEen COMEX-goudcontract is 100 troy ounce.\n"
        f"Bij een goudprijs van ${spot:,.2f} is dat:\n"
        f"\n"
        f"    100 ounce x ${spot:,.2f} = ${notional:,.0f}\n"
        f"\n"
        f"Dat heet de NOTIONELE WAARDE. Let op: dit bedrag betaal je NIET.\n"
        f"Het is alleen de maatstaf waarover je winst en verlies wordt berekend."
    )

    print(
        f"\nOm de positie te mogen openen stort je de INITIAL MARGIN,\n"
        f"ongeveer 5% van de notionele waarde:\n"
        f"\n"
        f"    5% x ${notional:,.0f} = ${initial:,.0f}\n"
        f"\n"
        f"Dit is GEEN aanbetaling en GEEN kostenpost. Het geld blijft van jou;\n"
        f"het staat alleen vast als onderpand. Sluit je de positie zonder\n"
        f"verlies, dan krijg je het volledig terug."
    )

    print(
        f"\nJe hebt dus voor ${notional:,.0f} aan goud in beweging\n"
        f"met ${initial:,.0f} op je rekening. Dat is een hefboom van {notional / initial:.0f}x.\n"
        f"\n"
        f"Daar zit meteen het risico: beweegt goud 1%, dan is dat\n"
        f"${notional * 0.01:,.0f} winst of verlies. Op een inleg van ${initial:,.0f}\n"
        f"is dat {notional * 0.01 / initial * 100:.0f}% van je geld. EEN DAG."
    )


def explain_dynamics() -> None:
    """Legt uit hoe mark-to-market en margin calls werken."""
    section("DEEL 2: HOE DE DYNAMIEK WERKT")

    print(
        "\nElke handelsdag gebeurt hetzelfde, in deze volgorde:\n"
        "\n"
        "  STAP 1  MARK-TO-MARKET\n"
        "          De beurs herrekent je positie tegen de slotkoers. Beweegt\n"
        "          de prijs tegen je in, dan gaat dat bedrag DIE DAG van je\n"
        "          rekening af.\n"
        "\n"
        "          Dit is geen papieren verlies dat je kunt uitzitten. Het\n"
        "          geld verdwijnt echt van je rekening, elke dag opnieuw.\n"
        "\n"
        "  STAP 2  CONTROLE OP DE ONDERGRENS\n"
        "          Er is een MAINTENANCE MARGIN: een ondergrens, meestal rond\n"
        "          90% van de initial margin. Zolang je saldo daarboven blijft,\n"
        "          gebeurt er niets.\n"
        "\n"
        "  STAP 3  MARGIN CALL\n"
        "          Zakt je saldo onder die grens, dan belt je broker: bijstorten,\n"
        "          meestal binnen een dag.\n"
        "\n"
        "          Belangrijk detail: je moet bijstorten tot de INITIAL margin,\n"
        "          niet tot de ondergrens. Een margin call vraagt dus MEER dan\n"
        "          het tekort dat je hebt.\n"
        "\n"
        "  STAP 4  ALS JE NIET STORT\n"
        "          De broker sluit je positie gedwongen. Je verlies wordt\n"
        "          definitief, en meestal gebeurt dat op het slechtste moment:\n"
        "          precies wanneer de markt tegen je in is doorgeschoten.\n"
        "\n"
        "DAAR IS JE CASH-BUFFER VOOR.\n"
        "Niet om het verlies te dekken - dat gebeurt sowieso - maar om te kunnen\n"
        "BIJSTORTEN, zodat je niet gedwongen wordt uitgestopt terwijl je hedge\n"
        "nog loopt.\n"
        "\n"
        "EEN EXTRA DRAAI DIE VAAK VERGETEN WORDT\n"
        "De margevereiste is een percentage van de NOTIONELE waarde, en die\n"
        "beweegt mee met de prijs. Bij een short positie werkt dat dubbel tegen\n"
        "je: goud stijgt, dus je verliest geld EN de eis wordt hoger."
    )


def walk_through_lehman(prices: pd.Series) -> None:
    """Loopt de Lehman-week dag voor dag door."""
    section("DEEL 3: EEN ECHT VOORBEELD - SEPTEMBER 2008")

    print(
        "\nDit is de zwaarste periode voor een short goudpositie in de hele\n"
        "reeks van 23 jaar. Lehman Brothers viel om op 15 september 2008, en\n"
        "beleggers vluchtten naar goud.\n"
        "\n"
        "Stel: je bent op 11 september short gegaan in 1 contract."
    )

    settings = MarginSettings(contracts=1, is_short=True)
    result = simulate_margin(prices, settings)

    print(
        f"\n  Instapprijs        ${prices.iloc[0]:,.2f}\n"
        f"  Notionele waarde   ${result.notional_start:,.0f}\n"
        f"  Initial margin     ${result.initial_margin:,.0f}  (5%)\n"
    )

    display = result.to_frame()
    for column in (
        "prijs",
        "dagresultaat",
        "saldo",
        "ondergrens",
        "bijstorten",
        "saldo_na",
        "totaal_gestort",
    ):
        display[column] = display[column].map(lambda v: f"{v:,.0f}")
    print(display.to_string(index=False))

    print(
        "\nHoe je deze tabel leest:\n"
        "  dagresultaat  wat er die dag van je rekening af ging (negatief)\n"
        "  saldo         je saldo NA het dagresultaat, VOOR het bijstorten\n"
        "  ondergrens    zakt het saldo hieronder, dan volgt een margin call\n"
        "  bijstorten    wat je die dag moest storten\n"
        "  saldo_na      je saldo na het bijstorten"
    )

    final_price = float(prices.iloc[-1])
    price_change = (final_price / float(prices.iloc[0]) - 1) * 100
    buffer_needed = result.peak_cash_needed

    print(
        f"\nDE UITKOMST\n"
        f"  Goud steeg van ${prices.iloc[0]:,.2f} naar ${final_price:,.2f} "
        f"(+{price_change:.1f}%)\n"
        f"  Aantal margin calls        {result.n_margin_calls}\n"
        f"  Grootste enkele call       ${result.largest_single_call:,.0f}\n"
        f"  Totaal moeten bijstorten   ${buffer_needed:,.0f}"
    )

    print(
        "\nTWEE GETALLEN DIE JE UIT ELKAAR MOET HOUDEN\n"
        "\n"
        f"  1. WAT JE BESCHIKBAAR MOEST HEBBEN:  ${buffer_needed:,.0f}\n"
        f"     ({buffer_needed / result.notional_start * 100:.1f}% van de notionele waarde)\n"
        "     Dit is wat je buffer moet dekken. Kon je dit niet ophoesten,\n"
        "     dan was je uitgestopt.\n"
        "\n"
        f"  2. WAT JE UITEINDELIJK KWIJT BENT:   ${result.net_loss:,.0f}\n"
        f"     ({result.net_loss / result.notional_start * 100:.1f}% van de notionele waarde)\n"
        "     Lager, want een deel van wat je stortte staat gewoon nog op je\n"
        f"     rekening: ${result.final_balance:,.0f}. Dat krijg je terug bij sluiten.\n"
        "\n"
        "Voor JOUW vraag telt getal 1. Je wilt niet uitgestopt worden, en\n"
        "daarvoor moet het geld ER ZIJN op het moment dat de broker belt -\n"
        "ook al krijg je een deel later terug."
    )

    print(
        "\nHIER ZIE JE HET PROBLEEM MET DE VUISTREGEL\n"
        f"Je had ${result.initial_margin:,.0f} gestort om de positie te openen.\n"
        f"In tien handelsdagen moest je daar ${buffer_needed:,.0f} bovenop leggen -\n"
        f"ruim {buffer_needed / result.initial_margin:.0f} keer je oorspronkelijke inleg.\n"
        "\n"
        f"Een buffer van 5% van de notionele waarde is ${result.notional_start * 0.05:,.0f}: "
        f"{'genoeg' if result.notional_start * 0.05 >= buffer_needed else 'NIET genoeg'}.\n"
        f"Een buffer van 10% is ${result.notional_start * 0.10:,.0f}: "
        f"{'genoeg' if result.notional_start * 0.10 >= buffer_needed else 'ook niet genoeg'}.\n"
        f"Je had ongeveer {buffer_needed / result.notional_start * 100:.0f}% nodig gehad.\n"
        "\n"
        "LET OP: dit is de ERGSTE periode uit 23 jaar. Zo'n buffer altijd\n"
        "aanhouden is overdreven duur. Dat is precies de afweging waar fase 4\n"
        "over gaat: hoeveel zekerheid wil je, en wat kost die?"
    )


def explain_percentile(returns: pd.Series) -> None:
    """Legt uit wat een 99%-grens betekent."""
    section("DEEL 4: WAT BETEKENT 'DE 99%-GRENS'?")

    print(
        "\nDe 99%-grens is geen voorspelling. Het is een uitspraak over hoe\n"
        "vaak iets voorkomt.\n"
        "\n"
        "Zo reken je hem uit:\n"
        "\n"
        "  1. Neem alle 10-daagse periodes uit 23 jaar historie.\n"
        "  2. Bereken voor elke periode hoeveel de prijs bewoog.\n"
        "  3. Sorteer die uitkomsten van laag naar hoog.\n"
        "  4. Pak de waarde waar 99% onder ligt.\n"
        "\n"
        "Dat getal betekent: IN 99 VAN DE 100 GEVALLEN BLEEF DE BEWEGING\n"
        "HIERONDER. In 1 van de 100 was hij groter."
    )

    horizon = 10
    cumulative = (np.exp(returns.rolling(horizon).sum()) - 1).dropna() * 100
    sorted_moves = np.sort(cumulative.values)
    n = len(sorted_moves)

    print(f"\nConcreet, met {n:,} overlappende periodes van {horizon} handelsdagen:")
    print(f"\n  {'percentiel':>12s}  {'stijging':>10s}   betekenis")
    print(f"  {'-' * 12}  {'-' * 10}   {'-' * 45}")
    for pct, meaning in (
        (50, "de helft van de periodes blijft hieronder"),
        (90, "9 van de 10"),
        (95, "19 van de 20"),
        (99, "99 van de 100  <-- dit gebruiken we"),
        (99.9, "999 van de 1000"),
    ):
        value = float(np.percentile(sorted_moves, pct))
        print(f"  {pct:>11.1f}%  {value:>9.1f}%   {meaning}")

    print(f"  {'maximum':>12s}  {sorted_moves[-1]:>9.1f}%   de ergste in 23 jaar")

    print(
        "\nWAAROM 99% EN NIET 100%?\n"
        "Omdat 100% niet bestaat. Er is altijd een scenario dat erger is dan\n"
        "wat je ooit hebt gezien - dat is precies wat dikke staarten betekenen.\n"
        "\n"
        "Je kiest dus bewust een zekerheidsniveau. 99% betekent: ik accepteer\n"
        "dat ik in 1 van de 100 gevallen tekortkom. Wil je 99,9%, dan heb je\n"
        "meer kapitaal nodig dat de rest van de tijd niets doet.\n"
        "\n"
        "Dat is een AFWEGING, geen technisch detail: meer zekerheid kost geld."
    )

    print(
        "\nDE VALKUIL BIJ DEZE BEREKENING\n"
        "Deze percentages komen uit de historie. Ze kennen alleen scenario's\n"
        "die echt gebeurd zijn. De ergste tien dagen uit 23 jaar zeggen niets\n"
        "over wat er volgend jaar kan gebeuren.\n"
        "\n"
        "Daarom simuleren we in fase 4 met een t-verdeling: die genereert ook\n"
        "scenario's die nog niet voorkwamen, maar wel passen bij hoe goud zich\n"
        "gedraagt. Dat is het verschil tussen 'wat gebeurde er' en 'wat kan er\n"
        "gebeuren'."
    )


def show_real_buffer_need(returns: pd.Series) -> None:
    """Berekent de echte buffer per horizon via historische simulatie."""
    section("DEEL 5: HOEVEEL BUFFER HAD JE ECHT NODIG?")

    print(
        "\nNu rekenen we het echt door: schuif een venster over de hele\n"
        "historie, simuleer de margerekening dag voor dag, en kijk hoeveel je\n"
        "had moeten bijstorten.\n"
        "\n"
        "Dit is dus niet 'hoeveel bewoog de prijs' maar 'hoeveel cash had ik\n"
        "nodig' - inclusief het feit dat de margevereiste meestijgt."
    )

    rows = []
    for horizon, label in ((5, "1 week"), (21, "1 maand"), (63, "1 kwartaal")):
        outcome = buffer_needed_for_confidence(
            returns, horizon_days=horizon, confidence=0.99, n_windows=900
        )
        rows.append(
            {
                "horizon": label,
                "mediaan": f"{outcome['median_pct']:.1f}%",
                "99%-grens": f"{outcome['buffer_pct']:.1f}%",
                "ergste": f"{outcome['worst_pct']:.1f}%",
                "kans op margin call": f"{outcome['share_with_margin_call']:.0%}",
            }
        )

    print(f"\n{pd.DataFrame(rows).to_string(index=False)}")

    print(
        "\nAls percentage van de notionele waarde, bovenop de initial margin.\n"
        "\n"
        "LEES DE MEDIAAN EN DE 99%-GRENS NAAST ELKAAR:\n"
        "In de helft van de gevallen heb je bijna niets nodig. Maar in het\n"
        "slechtste procent heb je veel nodig. Dat verschil IS het probleem met\n"
        "een vast percentage: je houdt bijna altijd te veel aan, en precies\n"
        "wanneer het ertoe doet te weinig.\n"
        "\n"
        "Een buffer die meebeweegt met de marktomstandigheden lost dat op.\n"
        "Dat is fase 4."
    )


def main() -> int:
    """Draait de uitleg."""
    pd.set_option("display.width", 150)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    gold = panel["gold_futures"].dropna()
    returns = compute_returns(panel, "gold_futures")

    print(LINE)
    print("HOE WERKT MARGE BIJ EEN FUTURES-POSITIE?")
    print(LINE)

    explain_basics(float(gold.iloc[-1]))
    explain_dynamics()

    lehman = gold.loc["2008-09-11":"2008-09-25"]
    walk_through_lehman(lehman)

    explain_percentile(returns)
    show_real_buffer_need(returns)

    section("SAMENVATTING")
    print(
        "\n1. Je betaalt niet de volle waarde maar ~5% als onderpand. Dat geld\n"
        "   blijft van jou; het staat vast zolang de positie loopt.\n"
        "\n"
        "2. Elke dag wordt je positie herrekend. Verlies gaat DIE DAG van je\n"
        "   rekening af - het is geen papieren verlies.\n"
        "\n"
        "3. Zakt je saldo onder de ondergrens, dan moet je bijstorten tot de\n"
        "   initial margin. Doe je dat niet, dan word je gedwongen uitgestopt.\n"
        "\n"
        "4. Je cash-buffer is er om te kunnen bijstorten. Niet om het verlies\n"
        "   te voorkomen, maar om niet uitgestopt te worden terwijl je hedge\n"
        "   nog loopt.\n"
        "\n"
        "5. De 99%-grens betekent: in 99 van de 100 gevallen was dit genoeg.\n"
        "   Niet 100%, want dat bestaat niet.\n"
        "\n"
        "6. Een vast percentage negeert dat de markt verandert. In rustige\n"
        "   tijden houd je te veel aan, in een crisis te weinig."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
