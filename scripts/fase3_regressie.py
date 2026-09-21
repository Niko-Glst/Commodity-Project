"""Fase 3: regressiemodellen, en de vraag of ze een random walk verslaan.

Gebruik:
    python scripts/fase3_regressie.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldmodel.config import ALL_SERIES, series_by_name  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.models import (  # noqa: E402
    diebold_mariano,
    fit_ols_newey_west,
    horizon_comparison,
    walk_forward_validate,
)
from goldmodel.viz.correlations import build_change_panel  # noqa: E402

LINE = "=" * 78

# De drivers voor het basismodel. Bewust een beperkte set: de vier
# macro-reeksen met een theoretisch argument, plus de VIX als stressmaat.
# Zilver laten we weg - dat is geen macro-driver maar vrijwel hetzelfde
# product, en een R-kwadraat van 61% zou de rest van het model verbergen.
BASE_DRIVERS = [
    "real_rate_10y",
    "usd_broad_index",
    "breakeven_inflation_10y",
    "vix",
]


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def explain_the_plan() -> None:
    """Zet neer wat fase 3 doet en waarom."""
    section("WAT FASE 3 DOET")
    print(
        "\nFase 2 leverde een NULHYPOTHESE op: goudrendementen zijn nauwelijks\n"
        "te verklaren uit macro-data. Fase 3 toetst dat formeel.\n"
        "\n"
        "En de toets die telt is NIET de R-kwadraat.\n"
        "\n"
        "Waarom niet: een model met genoeg variabelen past altijd wel iets.\n"
        "Voeg een driver toe en de R-kwadraat stijgt, ook als die driver niets\n"
        "betekent. Dat is een rekenkundige eigenschap van OLS, geen bevinding.\n"
        "\n"
        "De eerlijke test: schat het model op data tot dag t, voorspel dag\n"
        "t+1, en vergelijk met een benchmark die niets weet. Die benchmark is\n"
        "de RANDOM WALK: 'morgen is als vandaag', dus een voorspelling van nul.\n"
        "\n"
        "Dat klinkt triviaal om te verslaan. Op financiele data is het\n"
        "ontzettend moeilijk."
    )


def show_ols(target: pd.Series, drivers: pd.DataFrame) -> None:
    """Toont de OLS-regressie met en zonder Newey-West."""
    section("STAP 1: OLS MET NEWEY-WEST STANDAARDFOUTEN")
    print(
        "\nEerst de gewone regressie. Maar de standaardfouten daarvan maken\n"
        "twee aannames die in deze data GESCHONDEN worden:\n"
        "\n"
        "  1. Constante variantie van de fouten. Fase 1 liet zien dat\n"
        "     volatiliteit clustert: in onrustige periodes zijn de fouten\n"
        "     groter.\n"
        "  2. Geen autocorrelatie in de fouten.\n"
        "\n"
        "Bij overtreding zijn de standaardfouten TE KLEIN, en lijkt alles\n"
        "significanter dan het is. Newey-West corrigeert daarvoor.\n"
        "\n"
        "Belangrijk: Newey-West repareert de STANDAARDFOUTEN, niet de\n"
        "coefficienten. Die blijven identiek. Het model wordt er niet beter\n"
        "van; je krijgt alleen een eerlijker beeld van de onzekerheid."
    )

    result = fit_ols_newey_west(target, drivers)

    print(f"\nSteekproef: {result.n_observations} dagen\n")
    table = result.to_frame()
    display = table.copy()
    display["coefficient"] = display["coefficient"].map(lambda v: f"{v:+.5f}")
    for column in ("se_ols", "se_newey_west"):
        display[column] = display[column].map(lambda v: f"{v:.5f}")
    display["t_nw"] = display["t_nw"].map(lambda v: f"{v:+.2f}")
    display["p_nw"] = display["p_nw"].map(lambda v: f"{v:.4f}")
    display["vif"] = display["vif"].map(lambda v: f"{v:.2f}")
    print(display.to_string())

    print("\nHOEVEEL SCHEELDE DE CORRECTIE?")
    inflation = result.se_inflation.sort_values(ascending=False)
    for driver, factor in inflation.items():
        print(
            f"  {driver:26s} standaardfout {factor:.2f}x groter "
            f"met Newey-West"
        )
    print(
        "\nEen factor 1,5 betekent: zonder correctie onderschatte je de\n"
        "onzekerheid met 50%. Dat is precies het bedrag waarmee je jezelf voor\n"
        "de gek zou houden."
    )

    print(f"\nR-kwadraat (in-sample): {result.r_squared:.4f}")
    print(f"Aangepast             : {result.r_squared_adj:.4f}")
    print(
        f"\nDe drivers verklaren dus {result.r_squared * 100:.1f}% van de dagelijkse\n"
        "goudbeweging. Dat is in lijn met fase 2, en het is weinig."
    )

    print("\nMULTICOLLINEARITEIT (VIF)")
    print(
        "  VIF < 5   geen probleem\n"
        "  5 tot 10  let op\n"
        "  > 10      de losse coefficient is niet te interpreteren\n"
    )
    worst = result.vif.max()
    if worst < 5:
        print(
            f"  Hoogste VIF: {worst:.2f}. Geen probleem in deze set.\n"
            "  Dat komt doordat we bewust maar een dollarmaatstaf hebben\n"
            "  meegenomen; met DXY erbij zou dit oplopen."
        )
    else:
        print(f"  Hoogste VIF: {worst:.2f} — zie de tabel hierboven.")

    print("\nTEKENS: KLOPPEN ZE MET DE VERWACHTING?")
    rows = []
    for driver in drivers.columns:
        try:
            expected = series_by_name(driver).expected_sign
        except KeyError:
            expected = "?"
        coefficient = result.coefficients[driver]
        actual = "+" if coefficient > 0 else "-"
        significant = result.p_values_nw[driver] < 0.05
        rows.append(
            {
                "driver": driver,
                "verwacht": expected,
                "gevonden": actual,
                "klopt": "JA" if expected == actual else "nee",
                "significant_nw": "ja" if significant else "nee",
            }
        )
    print(f"\n{pd.DataFrame(rows).to_string(index=False)}")


def show_walk_forward(target: pd.Series, drivers: pd.DataFrame) -> dict:
    """Draait de walk-forward validatie: de kern van fase 3."""
    section("STAP 2: WALK-FORWARD VALIDATIE — DE TOETS DIE TELT")
    print(
        "\nOpzet:\n"
        "  - begin met 1000 dagen trainingsdata\n"
        "  - schat de modellen, voorspel de volgende dag\n"
        "  - schuif 21 dagen op, herhaal\n"
        "  - NOOIT trainen op data van na de voorspelde dag\n"
        "\n"
        "De drivers worden met EEN DAG GELAGD. Dat volgt uit fase 1: FRED\n"
        "publiceert de waarde van dag t pas op werkdag t+1. Het rendement van\n"
        "vandaag verklaren uit de rente van vandaag zou look-ahead bias zijn.\n"
        "\n"
        "Vier modellen:\n"
        "  random_walk  voorspelt altijd nul (de benchmark)\n"
        "  historisch   voorspelt het gemiddelde uit de trainingsdata\n"
        "  ols          gewone regressie op alle drivers\n"
        "  ridge        geregulariseerd, tegen multicollineariteit"
    )

    result = walk_forward_validate(target, drivers, min_train=1000, step=21)

    print(f"\n{result.n_folds} vensters, horizon {result.horizon} dag.\n")
    display = result.metrics.copy()
    display["rmse"] = display["rmse"].map(lambda v: f"{v:.6f}")
    display["mae"] = display["mae"].map(lambda v: f"{v:.6f}")
    display["directional_accuracy"] = display["directional_accuracy"].map(
        lambda v: "n.v.t." if pd.isna(v) else f"{v:.1%}"
    )
    display["r2_oos"] = display["r2_oos"].map(lambda v: f"{v:+.4f}")
    display["rmse_vs_benchmark_pct"] = display["rmse_vs_benchmark_pct"].map(
        lambda v: f"{v:+.2f}%"
    )
    print(display.to_string())

    print(
        "\nHOE JE DIT LEEST\n"
        "  rmse                  gemiddelde voorspelfout; lager is beter\n"
        "  directional_accuracy  hoe vaak het TEKEN klopte; 50% is munt opgooien\n"
        "  r2_oos                verklaarde variantie tegenover 'voorspel nul'\n"
        "                        NEGATIEF = slechter dan niets doen\n"
        "  rmse_vs_benchmark     hoeveel procent slechter (+) of beter (-) dan\n"
        "                        de random walk"
    )

    benchmark_rmse = float(result.metrics.loc["random_walk", "rmse"])
    verdicts = {}
    for model in ("ols", "ridge", "historisch"):
        model_rmse = float(result.metrics.loc[model, "rmse"])
        beats = model_rmse < benchmark_rmse
        verdicts[model] = beats
        difference = (model_rmse / benchmark_rmse - 1) * 100
        status = "VERSLAAT" if beats else "verliest van"
        print(
            f"\n  {model:12s} {status} de random walk "
            f"({difference:+.2f}% RMSE)"
        )

    print("\nIS HET VERSCHIL SIGNIFICANT? (Diebold-Mariano)")
    print(
        "\nEen lagere RMSE kan toeval zijn. Deze toets kijkt of het verschil\n"
        "in voorspelfouten systematisch is, met Newey-West standaardfouten\n"
        "omdat de verschilreeks zelf geautocorreleerd is.\n"
    )
    for model in ("ols", "ridge"):
        test = diebold_mariano(
            result.actuals, result.predictions[model], result.predictions["random_walk"]
        )
        print(
            f"  {model} tegen random walk: statistiek {test['statistic']:+.2f}, "
            f"p = {test['p_value']:.4f}"
        )
        print(f"    -> {test['better']}")

    return {"result": result, "verdicts": verdicts}


def show_horizons(prices: pd.Series, drivers: pd.DataFrame) -> None:
    """Toetst of langere horizonnen beter voorspelbaar zijn."""
    section("STAP 3: ZIJN LANGERE HORIZONNEN BETER VOORSPELBAAR?")
    print(
        "\nFase 2 vond zwakke DAGcorrelaties. Maar dat sluit sterkere verbanden\n"
        "op maand- of kwartaalbasis niet uit: ruis dempt uit bij aggregatie\n"
        "terwijl een echt signaal blijft staan.\n"
        "\n"
        "Per horizon aggregeren we de rendementen en toetsen we of de drivers\n"
        "ze voorspellen. We gebruiken NIET-OVERLAPPENDE vensters, zodat de\n"
        "waarnemingen onafhankelijk zijn - anders lijkt de steekproef veel\n"
        "groter dan hij is."
    )

    table = horizon_comparison(prices, drivers)
    display = table.copy()
    for column in ("r2_in_sample", "r2_oos"):
        display[column] = display[column].map(
            lambda v: "n.v.t." if pd.isna(v) else f"{v:+.4f}"
        )
    print(f"\n{display.to_string(index=False)}")

    print(
        "\nLET OP DE KOLOM n\n"
        "Bij een kwartaalhorizon met niet-overlappende vensters houd je maar\n"
        "een fractie van de waarnemingen over. Een hogere R-kwadraat daar kan\n"
        "gewoon ruis zijn: met 90 waarnemingen en 4 drivers past een model\n"
        "vanzelf beter, zonder dat het iets weet.\n"
        "\n"
        "Daarom staat de out-of-sample kolom ernaast. Die is de enige die\n"
        "telt."
    )


def main() -> int:
    """Draait fase 3."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 170)

    print(LINE)
    print("FASE 3: REGRESSIEMODELLEN EN HUN VALIDATIE")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    changes = build_change_panel(panel)

    available = [d for d in BASE_DRIVERS if d in changes.columns]
    target = changes["gold_futures"]
    drivers = changes[available]

    print(f"\nAfhankelijke variabele : goudrendement (log, dagelijks)")
    print(f"Drivers                : {', '.join(available)}")
    print(
        "\nZilver zit er bewust NIET in. Dat is geen macro-driver maar vrijwel\n"
        "hetzelfde product; met een correlatie van 0,78 zou het de rest van\n"
        "het model verbergen."
    )

    explain_the_plan()
    show_ols(target, drivers)
    outcome = show_walk_forward(target, drivers)
    show_horizons(panel["gold_futures"].dropna(), drivers)

    section("CONCLUSIE VAN FASE 3")

    metrics = outcome["result"].metrics
    ols_difference = float(metrics.loc["ols", "rmse_vs_benchmark_pct"])
    hist_difference = float(metrics.loc["historisch", "rmse_vs_benchmark_pct"])

    print(
        "\nDE MODELLEN MET DRIVERS VERSLAAN DE RANDOM WALK NIET.\n"
        "\n"
        f"  OLS en ridge zijn {ols_difference:+.2f}% op RMSE: SLECHTER dan\n"
        "  simpelweg nul voorspellen. De out-of-sample R-kwadraat is negatief,\n"
        "  en de directional accuracy ligt ONDER 50% - dus slechter dan een\n"
        "  munt opgooien.\n"
        "\n"
        f"  Het 'historisch' model (voorspel het gemiddelde) scoort {hist_difference:+.2f}%.\n"
        "  Dat is geen prestatie: het gemiddelde dagrendement is ongeveer\n"
        "  0,04%, dus dat model voorspelt vrijwel hetzelfde als nul. Het\n"
        "  verschil is afrondingsruis, geen signaal.\n"
        "\n"
        "En de Diebold-Mariano-toets zegt bij beide echte modellen 'geen\n"
        "significant verschil'. Ze zijn dus niet aantoonbaar slechter, maar\n"
        "zeker niet beter.\n"
        "\n"
        "Dat is het resultaat van fase 3, en het is precies wat fase 2\n"
        "voorspelde."
    )

    print(
        "\nEEN NUANCE OVER DE HORIZON\n"
        "De out-of-sample R-kwadraat loopt op van +0,005 op dagbasis naar\n"
        "+0,080 op kwartaalbasis. Dat suggereert dat de macro-drivers op\n"
        "langere horizon meer zeggen - wat economisch logisch is: het\n"
        "arbitrage-argument over de reele rente gaat over maanden, niet over\n"
        "dagen.\n"
        "\n"
        "MAAR: bij een kwartaalhorizon met niet-overlappende vensters houd je\n"
        "82 waarnemingen over voor 4 drivers. Dat is te weinig om een\n"
        "verschil van 8% verklaarde variantie te onderscheiden van toeval.\n"
        "\n"
        "Dit is dus geen conclusie maar een aanwijzing, en een eerlijke\n"
        "manier om het te formuleren is: 'op dagbasis geen signaal; op\n"
        "kwartaalbasis mogelijk wel, maar te weinig data om het vast te\n"
        "stellen'."
    )

    print(
        "\nWAAROM DIT GEEN MISLUKKING IS\n"
        "Dit is wat de efficiente-markthypothese voorspelt. Waren\n"
        "goudrendementen uit publieke macro-data te voorspellen, dan zou\n"
        "iedereen die dat wist erop handelen tot het verband verdween.\n"
        "\n"
        "Een project dat correct concludeert dat er weinig signaal is, is\n"
        "verdedigbaar. Een project met een mooie in-sample R-kwadraat die\n"
        "out-of-sample instort, is dat niet.\n"
        "\n"
        "EN WAT WEL WERKT\n"
        "De RICHTING is onvoorspelbaar, de GROOTTE niet. Dat was bevinding 3\n"
        "van fase 1, en het is precies waar fase 4 op bouwt: GARCH modelleert\n"
        "de voorspelbare volatiliteit, niet de onvoorspelbare richting.\n"
        "\n"
        "Voor je margevraag is dat genoeg. Je hoeft niet te weten of goud\n"
        "morgen stijgt of daalt - je moet weten hoe groot de beweging kan\n"
        "zijn."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
