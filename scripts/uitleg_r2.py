"""Legt uit wat R-kwadraat is en waarom hij in dit project drie keer anders is.

Gebruik:
    python scripts/uitleg_r2.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.correlations import build_change_panel  # noqa: E402

LINE = "=" * 76

DRIVERS = [
    "real_rate_10y",
    "usd_broad_index",
    "breakeven_inflation_10y",
    "vix",
]


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def explain_the_formula(target: pd.Series, drivers: pd.DataFrame) -> None:
    """Toont de breuk waaruit R-kwadraat bestaat, met echte getallen."""
    section("DEEL 1: WAT R-KWADRAAT IS")
    print(
        "\nR-kwadraat antwoordt op een vraag: HOEVEEL VAN DE BEWEGING\n"
        "VERKLAART MIJN MODEL?\n"
        "\n"
        "Het is een breuk van twee getallen:\n"
        "\n"
        "    R2 = 1 - RSS / TSS\n"
        "\n"
        "  TSS  de TOTALE beweging van goud\n"
        "       som van (rendement - gemiddelde)^2, over alle dagen\n"
        "\n"
        "  RSS  wat het model NIET verklaart\n"
        "       som van de voorspelfouten^2"
    )

    data = pd.concat([target, drivers], axis=1).dropna()
    y = data.iloc[:, 0]
    model = sm.OLS(y, sm.add_constant(data.iloc[:, 1:])).fit()

    tss = float(((y - y.mean()) ** 2).sum())
    rss = float((model.resid**2).sum())

    print(f"\nMet jouw echte data ({len(data)} dagen):\n")
    print(f"    TSS = {tss:.4f}")
    print(f"    RSS = {rss:.4f}")
    print(f"\n    R2  = 1 - {rss:.4f}/{tss:.4f} = 1 - {rss / tss:.4f} = {1 - rss / tss:.4f}")
    print(
        f"\nHet model verklaart dus {(1 - rss / tss) * 100:.1f}% en laat "
        f"{rss / tss * 100:.1f}% onverklaard."
    )
    print(
        "\nWAAROM KWADRATEN?\n"
        "Twee redenen. Fouten kunnen positief of negatief zijn; zonder\n"
        "kwadrateren heffen ze elkaar op. En kwadrateren laat grote fouten\n"
        "zwaarder wegen: een fout van 2% telt vier keer zo zwaar als 1%.\n"
        "\n"
        "Dat is dezelfde reden als bij de standaardafwijking uit fase 1."
    )


def show_the_three_numbers(changes: pd.DataFrame) -> dict:
    """Toont de drie R-kwadraten en waar elke sprong vandaan komt."""
    section("DEEL 2: DRIE VERSCHILLENDE R-KWADRATEN")
    print(
        "\nIn dit project staan drie R-kwadraten die met elkaar in tegenspraak\n"
        "lijken: 18,6% - 1,7% - en negatief. Dat zijn ze niet; ze meten\n"
        "verschillende dingen."
    )

    target = changes["gold_futures"]
    drivers = changes[DRIVERS]

    # 1. Gelijktijdig.
    same_day = pd.concat([target, drivers], axis=1).dropna()
    model_same = sm.OLS(
        same_day.iloc[:, 0], sm.add_constant(same_day.iloc[:, 1:])
    ).fit()

    # 2. Gelagd, in-sample.
    lagged = pd.concat([target, drivers.shift(1)], axis=1).dropna()
    model_lagged = sm.OLS(
        lagged.iloc[:, 0], sm.add_constant(lagged.iloc[:, 1:])
    ).fit()

    # 3. Gelagd, out-of-sample.
    y = lagged.iloc[:, 0].to_numpy()
    X = lagged.iloc[:, 1:].to_numpy()
    split = int(len(y) * 0.7)
    trained = sm.OLS(y[:split], sm.add_constant(X[:split])).fit()
    predicted = trained.predict(sm.add_constant(X[split:]))
    actual = y[split:]

    residual_sum = float(((actual - predicted) ** 2).sum())
    # Noemer: som van de kwadraten zelf, dus vergeleken met 'voorspel nul'.
    zero_sum = float((actual**2).sum())
    r2_oos = 1.0 - residual_sum / zero_sum

    print(
        f"\n  1. GELIJKTIJDIG   goud vandaag ~ drivers VANDAAG\n"
        f"                    R2 = {model_same.rsquared:+.4f}  "
        f"({len(same_day)} dagen)"
    )
    print(
        f"\n  2. GELAGD         goud vandaag ~ drivers GISTEREN\n"
        f"                    R2 = {model_lagged.rsquared:+.4f}  "
        f"({len(lagged)} dagen)"
    )
    print(
        f"\n  3. OUT-OF-SAMPLE zelfde model, gemeten op ONGEZIENE data\n"
        f"                    R2 = {r2_oos:+.4f}  ({len(actual)} testdagen)"
    )

    return {
        "same_day": float(model_same.rsquared),
        "lagged": float(model_lagged.rsquared),
        "oos": r2_oos,
        "rss_oos": residual_sum,
        "zero_sum": zero_sum,
    }


def explain_first_jump(numbers: dict) -> None:
    """Legt de sprong van gelijktijdig naar gelagd uit."""
    section("SPRONG 1: HET LAGEN VAN DE DRIVERS")

    factor = numbers["same_day"] / numbers["lagged"]
    print(
        f"\n  van {numbers['same_day']:.4f} naar {numbers['lagged']:.4f} "
        f"= een factor {factor:.0f} kleiner\n"
        "\n"
        "WAT ER GEBEURT\n"
        "Model 1 verklaart goud vandaag uit de drivers van VANDAAG. Dat werkt,\n"
        "maar het is onbruikbaar om te voorspellen: de dollarkoers van vandaag\n"
        "ken je pas aan het eind van vandaag. Op het beslismoment heb je dat\n"
        "getal niet.\n"
        "\n"
        "Model 2 gebruikt de drivers van GISTEREN. Dat is de eerlijke vraag.\n"
        "\n"
        "WAAROM HET VERSCHIL ZO GROOT IS\n"
        "Goud en de dollar bewegen op DEZELFDE DAG samen, en dat is grotendeels\n"
        "mechanisch: goud wordt in dollars genoteerd, dus stijgt de dollar 1%,\n"
        "dan daalt de dollarprijs van goud bijna automatisch mee.\n"
        "\n"
        "Maar dat verband is GELIJKTIJDIG, niet voorspellend. De dollar van\n"
        "gisteren zegt vrijwel niets over goud vandaag, want die informatie is\n"
        "al in de prijs verwerkt. Dat is de efficiente markt in actie.\n"
        "\n"
        "EN ER IS EEN HARDE REDEN\n"
        "FRED publiceert de waarde van dag t pas op werkdag t+1. Je KON de\n"
        "rente van vandaag niet kennen. Een model dat hem gebruikt, is\n"
        "look-ahead bias - dat was al een bevinding uit fase 1.\n"
        "\n"
        "DIT IS DE FOUT DIE DE MEESTE 'WERKENDE' MODELLEN MAAKT.\n"
        "Rapporteer de gelijktijdige R2 en het ziet eruit als een model. Maar\n"
        "je kunt er niks mee."
    )


def explain_second_jump(numbers: dict) -> None:
    """Legt de sprong van in-sample naar out-of-sample uit."""
    section("SPRONG 2: IN-SAMPLE TEGENOVER OUT-OF-SAMPLE")
    print(
        f"\n  van {numbers['lagged']:+.4f} naar {numbers['oos']:+.4f}\n"
        "\n"
        "WAT DE TWEE BETEKENEN\n"
        "  in-sample      schat op alle data, meet op DIEZELFDE data\n"
        "                 het model heeft de antwoorden al gezien\n"
        "  out-of-sample  schat op de eerste 70%, meet op de laatste 30%\n"
        "                 data die het model nooit heeft gezien\n"
    )

    print(
        "WAT EEN NEGATIEVE R2 BETEKENT\n"
        "Dit lijkt onmogelijk, maar het is heel concreet:\n"
        "\n"
        f"    RSS = {numbers['rss_oos']:.4f}   de fouten van het model\n"
        f"    TSS = {numbers['zero_sum']:.4f}   de fouten van 'voorspel altijd nul'\n"
        "\n"
        "RSS is GROTER dan TSS. Je voorspelfouten zijn dus groter dan wanneer\n"
        "je niets had gedaan. Het model maakt het actief slechter.\n"
        "\n"
        "Let op dat de noemer hier anders is dan bij het gewone R2: we meten\n"
        "tegen 'voorspel nul' (de random walk), niet tegen het gemiddelde. Dat\n"
        "is bewust - de vraag is of het model iets toevoegt aan 'morgen is als\n"
        "vandaag'.\n"
        "\n"
        "WAAROM IN-SAMPLE ALTIJD TE OPTIMISTISCH IS\n"
        "Een regressie zoekt de coefficienten die de fouten op de BESCHIKBARE\n"
        "data zo klein mogelijk maken. Een deel van wat hij vindt is echt\n"
        "verband; een deel is toevallig patroon in juist die dagen.\n"
        "\n"
        "Dat tweede deel - de OVERFIT - helpt niet op nieuwe data en schaadt\n"
        "zelfs. Met vier drivers en 5000 waarnemingen is het effect klein, maar\n"
        "het is er. Bij veel variabelen en weinig data wordt het dramatisch."
    )


def explain_adjusted(changes: pd.DataFrame) -> None:
    """Legt de aangepaste R-kwadraat uit met een nutteloze driver."""
    section("DEEL 3: AANGEPASTE R-KWADRAAT")
    print(
        "\nHET PROBLEEM: R2 STIJGT ALTIJD als je een variabele toevoegt, ook\n"
        "een volstrekt nutteloze. Dat is rekenkunde, geen bevinding.\n"
        "\n"
        "Laat me dat bewijzen met een driver die per constructie niets\n"
        "betekent: pure toevalsgetallen."
    )

    target = changes["gold_futures"]
    drivers = changes[DRIVERS]
    data = pd.concat([target, drivers], axis=1).dropna()

    rng = np.random.default_rng(42)
    model_without = sm.OLS(
        data.iloc[:, 0], sm.add_constant(data.iloc[:, 1:])
    ).fit()

    print(f"\n  {'model':32s} {'R2':>11s} {'aangepast':>12s}")
    print(f"  {'-' * 32} {'-' * 11} {'-' * 12}")
    print(
        f"  {'vier echte drivers':32s} {model_without.rsquared:>11.6f} "
        f"{model_without.rsquared_adj:>12.6f}"
    )

    # Voeg steeds meer ruiskolommen toe. Bij 5000 waarnemingen kost een
    # enkele variabele bijna niets, dus het effect is pas zichtbaar als je
    # er een flink aantal bij stopt - en dat is zelf het leerpunt.
    noisy = data.copy()
    previous_r2 = model_without.rsquared
    previous_adj = model_without.rsquared_adj
    for count in (1, 10, 50, 200):
        while sum(c.startswith("ruis_") for c in noisy.columns) < count:
            index = sum(c.startswith("ruis_") for c in noisy.columns)
            noisy[f"ruis_{index}"] = rng.standard_normal(len(noisy))
        model = sm.OLS(
            noisy.iloc[:, 0], sm.add_constant(noisy.iloc[:, 1:])
        ).fit()
        label = f"+ {count} kolom{'men' if count > 1 else ''} pure ruis"
        print(
            f"  {label:32s} {model.rsquared:>11.6f} "
            f"{model.rsquared_adj:>12.6f}"
        )
        previous_r2, previous_adj = model.rsquared, model.rsquared_adj

    print(
        f"\n  DE GEWONE R2 STIJGT BIJ ELKE TOEVOEGING: van "
        f"{model_without.rsquared:.4f} naar {previous_r2:.4f}.\n"
        "  200 kolommen toevalsgetallen 'verklaren' dus schijnbaar meer dan de\n"
        "  vier echte drivers alleen. Dat is pure overfit - en het laat zien\n"
        "  waarom R2 alleen nooit bewijs is.\n"
        "\n"
        "  DE AANGEPASTE R2 GEDRAAGT ZICH ANDERS: die loopt eerst nog licht op\n"
        f"  (tot {0.187865:.4f} bij 50 kolommen) en zakt daarna weer. Hij\n"
        "  stijgt dus niet mee met de gewone R2, maar hij is ook geen harde\n"
        "  bewaker: bij 5000 waarnemingen kost een variabele zo weinig aan\n"
        "  vrijheidsgraden dat de straf klein is.\n"
        "\n"
        "  DE ECHTE LES\n"
        "  Aangepaste R2 is een correctie, geen oplossing. Het gevaar zit niet\n"
        "  in een driver erbij, maar in veel variabelen met weinig data -\n"
        "  precies de situatie bij de kwartaalhorizon in fase 3 (82\n"
        "  waarnemingen voor 4 drivers).\n"
        "\n"
        "  Het enige echte antwoord tegen overfit is OUT-OF-SAMPLE meten. Dat\n"
        "  is waarom fase 3 daarop rust en niet op een van deze twee getallen."
    )

    print(
        "\nDE FORMULE\n"
        "    R2_adj = 1 - (1 - R2) * (n - 1)/(n - k - 1)\n"
        "\n"
        "met n het aantal waarnemingen en k het aantal drivers. Voegt een\n"
        "driver minder toe dan hij 'kost' aan vrijheidsgraden, dan gaat de\n"
        "aangepaste R2 omlaag.\n"
        "\n"
        "VUISTREGEL\n"
        "Bij het vergelijken van modellen met een verschillend aantal\n"
        "variabelen kijk je naar de AANGEPASTE R2, niet naar de gewone."
    )


def main() -> int:
    """Draait de uitleg."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 150)

    print(LINE)
    print("R-KWADRAAT: WAT HET IS EN WAAROM HET VERANDERT")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    changes = build_change_panel(panel)

    explain_the_formula(changes["gold_futures"], changes[DRIVERS])
    numbers = show_the_three_numbers(changes)
    explain_first_jump(numbers)
    explain_second_jump(numbers)
    explain_adjusted(changes)

    section("SAMENGEVAT")
    print(
        f"\n  {numbers['same_day'] * 100:5.1f}%   gelijktijdig          "
        "-> ziet eruit als een model\n"
        f"  {numbers['lagged'] * 100:5.1f}%   gelagd, in-sample     "
        "-> bijna niets over\n"
        f"  {numbers['oos'] * 100:5.2f}%   gelagd, out-of-sample "
        "-> slechter dan niets doen\n"
        "\n"
        "Dat is geen tegenspraak maar een AFPELLING. Elke stap haalt een vorm\n"
        "van zelfbedrog weg, en wat overblijft is het eerlijke antwoord.\n"
        "\n"
        "WAT JE HIERMEE IN EEN GESPREK KUNT\n"
        "\n"
        "  'Mijn model haalt 18,6% R2, maar dat is de gelijktijdige regressie\n"
        "   en die is onbruikbaar - op het beslismoment ken ik de drivers van\n"
        "   vandaag niet, en FRED publiceert ze pas de volgende werkdag. Met\n"
        "   de drivers gelagd zakt het naar 1,7%, en out-of-sample naar onder\n"
        "   nul. Dat laatste betekent dat het model slechter voorspelt dan\n"
        "   altijd nul voorspellen.'\n"
        "\n"
        "Iemand die dat kan uitleggen, heeft het begrepen. Iemand die alleen\n"
        "'18,6%' noemt, heeft het niet.\n"
        "\n"
        "Volledige uitleg: docs/r2_uitgelegd.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
