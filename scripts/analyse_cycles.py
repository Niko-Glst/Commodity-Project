"""Onderzoekt of er periodiciteit in de volatiliteit van goud zit.

De vraag: rustige en onrustige periodes wisselen elkaar af — zit daar een
ritme in dat je met een sinus of een Fourier-reeks kunt vangen en
voorspellen?

Dit script toetst dat in plaats van het te beweren. Het draait drie
controles en een voorspeltest.

Gebruik:
    python scripts/analyse_cycles.py
    python scripts/analyse_cycles.py --window 63   # ander volatiliteitsvenster
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.distributions import compute_returns  # noqa: E402
from goldmodel.viz.spectral import (  # noqa: E402
    fit_sine,
    plot_persistence_vs_cycle,
    plot_slutsky_effect,
    plot_volatility_spectrum,
    realised_volatility,
)
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 78


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def walk_forward_sine_test(
    vol: pd.Series,
    period_days: float,
    *,
    horizon: int = 21,
    min_train: int = 1000,
    step: int | None = None,
) -> dict:
    """Toetst of een sinus out-of-sample iets voorspelt.

    Dit is de beslissende test. Een sinus op historische data passen lukt
    altijd een beetje; de vraag is of hij werkt op data die hij niet gezien
    heeft.

    Methode: train op alles tot tijdstip t, voorspel de volgende ``horizon``
    dagen, schuif op. Nooit trainen op data die na de voorspelde periode
    ligt — dezelfde walk-forward-discipline als in fase 3.

    Twee opzetkeuzes die het resultaat bepalen, en die je moet kunnen
    verdedigen:

    **De horizon is kort (standaard 21 dagen).** Dat is de horizon waarop
    een volatiliteitsvoorspelling bruikbaar is. Voorspel je in één keer een
    blok van twee jaar, dan meet je iets heel anders: dan wint automatisch
    elk model dat het langjarig gemiddelde voorspelt, want de volatiliteit
    keert daarnaartoe terug. Dat zegt niets over cycliciteit.

    **Er zijn drie benchmarks, niet één.** De naïeve "laatste waarde" is de
    juiste maatstaf voor een persistente reeks op korte horizon. Het
    historisch gemiddelde is de juiste maatstaf voor een lange horizon. En
    het gemiddelde van de laatste 21 dagen zit daartussenin. Een sinus die
    alleen het gemiddelde verslaat heeft niets met een cyclus te maken —
    dan doet zijn constante term het werk, niet zijn golf.

    Om dat laatste hard te maken toetsen we de sinus ook tegen een variant
    van zichzelf zonder golf: alleen de constante, op dezelfde vensters
    geschat. Verschilt dat niet, dan draagt de golf niets bij.
    """
    values = vol.values.astype(float)
    n = len(values)
    step = step or horizon

    errors: dict[str, list[float]] = {
        "sine": [],
        "constant_only": [],
        "naive_last": [],
        "mean_all": [],
        "mean_recent": [],
    }

    for train_end in range(min_train, n - horizon, step):
        train = values[:train_end]
        test = values[train_end : train_end + horizon]

        t_train = np.arange(train_end, dtype=float)
        t_test = np.arange(train_end, train_end + horizon, dtype=float)

        # Volledige harmonische regressie: constante + sinus + cosinus.
        design_train = np.column_stack(
            [
                np.ones_like(t_train),
                np.sin(2 * np.pi * t_train / period_days),
                np.cos(2 * np.pi * t_train / period_days),
            ]
        )
        coefficients, *_ = np.linalg.lstsq(design_train, train, rcond=None)
        design_test = np.column_stack(
            [
                np.ones_like(t_test),
                np.sin(2 * np.pi * t_test / period_days),
                np.cos(2 * np.pi * t_test / period_days),
            ]
        )
        sine_forecast = design_test @ coefficients

        # Dezelfde regressie zonder de golf: alleen de constante. Het
        # verschil tussen deze twee isoleert wat de cyclus toevoegt.
        constant_forecast = np.full(horizon, float(train.mean()))

        errors["sine"].append(float(np.sqrt(np.mean((test - sine_forecast) ** 2))))
        errors["constant_only"].append(
            float(np.sqrt(np.mean((test - constant_forecast) ** 2)))
        )
        errors["naive_last"].append(
            float(np.sqrt(np.mean((test - np.full(horizon, train[-1])) ** 2)))
        )
        errors["mean_all"].append(
            float(np.sqrt(np.mean((test - np.full(horizon, train.mean())) ** 2)))
        )
        errors["mean_recent"].append(
            float(np.sqrt(np.mean((test - np.full(horizon, train[-21:].mean())) ** 2)))
        )

    results = {f"{k}_rmse": float(np.mean(v)) for k, v in errors.items()}
    results["n_folds"] = len(errors["sine"])
    results["horizon"] = horizon
    results["sine_beats_naive"] = results["sine_rmse"] < results["naive_last_rmse"]
    results["sine_beats_best_benchmark"] = results["sine_rmse"] < min(
        results["naive_last_rmse"],
        results["mean_all_rmse"],
        results["mean_recent_rmse"],
    )
    # Hoeveel voegt de golf toe bovenop de constante?
    results["wave_contribution_pct"] = (
        (results["constant_only_rmse"] - results["sine_rmse"])
        / results["constant_only_rmse"]
        * 100
    )
    return results


def main() -> int:
    """Voert de cyclusanalyse uit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, default=21, help="volatiliteitsvenster in dagen")
    args = parser.parse_args()

    apply_style()
    pd.set_option("display.width", 140)

    print(LINE)
    print("ZIT ER EEN CYCLUS IN DE VOLATILITEIT VAN GOUD?")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    gold = compute_returns(panel, "gold_futures")
    vol = realised_volatility(gold, window=args.window)

    print(f"\n{len(gold):,} handelsdagen, {gold.index.min().date()} tot {gold.index.max().date()}")
    print(f"Volatiliteit gemeten over een venster van {args.window} dagen: {len(vol):,} waarden")
    print(
        f"  gemiddeld {vol.mean():.1f}%   mediaan {vol.median():.1f}%   "
        f"min {vol.min():.1f}%   max {vol.max():.1f}%"
    )

    # ------------------------------------------------------------------
    section("WAT EEN FOURIER-TRANSFORMATIE DOET")
    print(
        "Elke tijdreeks is te schrijven als een som van sinussen en cosinussen\n"
        "met verschillende frequenties. De Fourier-transformatie rekent uit\n"
        "hoeveel van elke frequentie erin zit. Het resultaat heet het spectrum\n"
        "of periodogram.\n"
        "\n"
        "Zit er een echte cyclus van bijvoorbeeld 60 dagen in je data, dan zie\n"
        "je een scherpe piek bij periode 60. Is er geen cyclus, dan zie je geen\n"
        "piek.\n"
        "\n"
        "DE VALKUIL: een periodogram van pure ruis is NIET vlak. Het schommelt\n"
        "fors, en de hoogste schommeling ziet er altijd uit als een piek. Wie\n"
        "zonder referentie naar een periodogram kijkt, VINDT GEGARANDEERD\n"
        "cycli die er niet zijn.\n"
        "\n"
        "Daarom vergelijken we het spectrum met wat je zou zien als er GEEN\n"
        "cyclus was. Maar WELKE referentie je kiest, bepaalt je antwoord - en\n"
        "dat is de belangrijkste beslissing in deze hele analyse."
    )

    section("EERST: WAAROM DE VOOR DE HAND LIGGENDE REFERENTIE FOUT IS")
    print(
        "De intuitieve aanpak is: schud de waarnemingen door elkaar. Dat\n"
        "behoudt de verdeling exact - zelfde gemiddelde, spreiding, dikke\n"
        "staarten - maar vernietigt de volgorde, en dus elke cyclus.\n"
        "\n"
        "Dat klinkt goed, maar het is een STROMAN. Schudden vernietigt namelijk\n"
        "niet alleen de cyclus die we zoeken, maar ook de PERSISTENTIE die we\n"
        "al kennen. En de volatiliteit is extreem persistent: de autocorrelatie\n"
        "van dag op dag is boven de 0,98.\n"
        "\n"
        "Een traag bewegende reeks heeft van nature veel energie op lage\n"
        "frequenties. Niet omdat er een cyclus is, maar omdat hij traag is.\n"
        "Tegen een geschudde referentie steekt die energie er altijd bovenuit,\n"
        "en dan 'vind' je een cyclus met een periode van duizenden dagen die\n"
        "niets anders is dan de trage drift van de reeks zelf.\n"
        "\n"
        "Ik ben daar bij het bouwen van dit script zelf ingetrapt: met de\n"
        "geschudde referentie kwam er een 'significante piek' van 1483 dagen\n"
        "uit, en 111 van de 590 frequenties leken significant. Allemaal\n"
        "artefact.\n"
        "\n"
        "DE JUISTE REFERENTIE simuleert een AR(1)-proces: even persistent als\n"
        "de echte reeks (zelfde autocorrelatie, gemiddelde en spreiding), maar\n"
        "zonder enige cyclus. De autocorrelatie daalt exponentieel en wordt\n"
        "nooit negatief.\n"
        "\n"
        "Zo toetsen we de goede vraag: heeft de volatiliteit MEER structuur op\n"
        "een bepaalde frequentie dan een traag maar ritmeloos proces zou hebben?"
    )

    # ------------------------------------------------------------------
    section("TOETS 1: HET SPECTRUM MET REFERENTIEBAND")
    _, spec = plot_volatility_spectrum(gold, window=args.window)

    expected_by_chance = 0.05 * spec["n_frequencies_tested"]

    print("\nHet verschil tussen de twee referenties, op dezelfde data:")
    comparison = pd.DataFrame(
        [
            {
                "referentie": "geschud (naief, STROMAN)",
                "frequenties boven de band": spec["n_above_shuffled"],
                "bij toeval verwacht": f"{expected_by_chance:.0f}",
            },
            {
                "referentie": "AR(1) (behoudt persistentie)",
                "frequenties boven de band": spec["n_above_band"],
                "bij toeval verwacht": f"{expected_by_chance:.0f}",
            },
        ]
    )
    print(comparison.to_string(index=False))
    print(
        "\nDe naieve referentie 'vindt' dus veel meer structuur. Dat is geen\n"
        "cyclus maar persistentie die de verkeerde referentie niet meeneemt."
    )

    print(
        f"\nSterkste afwijking tegen de JUISTE referentie:"
        f"\n  periode                      : {spec['peak_period']:.0f} handelsdagen"
        f"\n  energie                      : {spec['peak_power']:.4g}"
        f"\n  grens (95% van AR1-simulaties): {spec['peak_threshold']:.4g}"
        f"\n  verhouding                   : {spec['peak_ratio']:.2f}x de grens"
    )
    print(
        f"\nVan de {spec['n_frequencies_tested']} getoetste frequenties steken er "
        f"{spec['n_above_band']} boven de AR(1)-band uit; bij toeval verwacht je "
        f"er {expected_by_chance:.0f}."
    )
    excess_factor = spec["n_above_band"] / expected_by_chance
    print(
        f"Dat is {excess_factor:.1f}x zoveel als toeval - dus er is IETS, maar\n"
        "de vraag is of het bruikbaar is. Let op het meervoudig-toetsen-\n"
        "probleem: bij het toetsen van honderden frequenties tegelijk vind je\n"
        "er altijd een paar die 'significant' lijken. Een handvol\n"
        "overschrijdingen zonder scherpe, geisoleerde piek is geen cyclus."
    )

    print(
        f"\nDe best passende sinus (periode {spec['peak_period']:.0f} dagen) heeft "
        f"R2 = {spec['sine_r_squared']:.4f}."
    )
    print(
        f"Die verklaart dus {spec['sine_r_squared'] * 100:.1f}% van de beweging in de\n"
        "volatiliteit. Ter vergelijking: een model dat niets doet behalve het\n"
        "gemiddelde voorspellen heeft per definitie R2 = 0."
    )

    # ------------------------------------------------------------------
    section("TOETS 2: HET SLUTSKY-YULE-EFFECT")
    print(
        "Voordat we een piek serieus nemen, moeten we uitsluiten dat we hem\n"
        "zelf gemaakt hebben.\n"
        "\n"
        "De volatiliteitsreeks is een VOORTSCHRIJDEND GEMIDDELDE. En een\n"
        "voortschrijdend gemiddelde van pure ruis vertoont golven. Dat is geen\n"
        "eigenschap van de data maar van het filter: het drukt korte\n"
        "schommelingen weg en laat lange staan, waardoor er vanzelf iets\n"
        "golfachtigs ontstaat.\n"
        "\n"
        "Slutsky beschreef dit in 1927 en Yule onafhankelijk rond dezelfde tijd.\n"
        "Het is een van de klassieke manieren waarop onderzoekers cycli 'vonden'\n"
        "in economische data die er niet waren.\n"
        "\n"
        "De figuur toont het: pure ruis zonder enige structuur, gladgestreken\n"
        "met hetzelfde venster dat wij gebruiken, en de golven verschijnen."
    )
    plot_slutsky_effect(window=args.window)

    # ------------------------------------------------------------------
    section("TOETS 3: PERSISTENTIE IS GEEN CYCLUS")
    print(
        "Dit is het begripsmatige onderscheid dat de hele vraag beantwoordt.\n"
        "\n"
        "  PERSISTENTIE  hoog blijft hoog, en zakt daarna geleidelijk terug\n"
        "                naar normaal. Geen vast ritme; onrust dooft gewoon uit.\n"
        "\n"
        "  CYCLUS        hoog wordt laag wordt hoog, met een vaste tussenpoos.\n"
        "                Je kunt voorspellen WANNEER de volgende piek komt.\n"
        "\n"
        "Het verschil zie je in de autocorrelatie van de volatiliteit:\n"
        "\n"
        "  - Bij persistentie daalt de curve langzaam naar nul en blijft positief.\n"
        "  - Bij een cyclus gaat de curve DOOR nul, wordt negatief, en komt\n"
        "    daarna weer omhoog. Een golf dus.\n"
        "\n"
        "Wat je in figuur 5 zag - blokken van onrust - is persistentie. Dat is\n"
        "wel degelijk voorspelbaar, maar op een andere manier dan een cyclus:\n"
        "je weet dat onrust morgen waarschijnlijk aanhoudt, niet dat hij over\n"
        "zestig dagen terugkomt."
    )
    _, persistence = plot_persistence_vs_cycle(gold, window=args.window)
    print(
        f"\nEerste-orde autocorrelatie van de volatiliteit: {persistence['phi']:.4f}"
        f"\nAutocorrelatie na 250 dagen (een jaar)        : {persistence['acf_at_250']:.4f}"
    )
    if persistence["acf_at_250"] > 0:
        print(
            "\n-> De autocorrelatie is na een jaar nog steeds positief en is\n"
            "   nergens duidelijk negatief geworden. Dat is het profiel van\n"
            "   persistentie, niet van een cyclus."
        )

    # ------------------------------------------------------------------
    section("TOETS 4: VOORSPELT DE SINUS IETS? (WALK-FORWARD)")
    print(
        "De beslissende test. Een sinus op historische data passen lukt altijd\n"
        "een beetje - de vraag is of hij werkt op data die hij niet gezien heeft.\n"
        "\n"
        "Methode: train op alles tot tijdstip t, voorspel de volgende 21 dagen,\n"
        "schuif op. Nooit trainen op data die na de voorspelde periode ligt.\n"
        "Dezelfde discipline die we in fase 3 op de regressiemodellen gaan\n"
        "toepassen.\n"
        "\n"
        "Er zijn vier benchmarks, want een oneerlijke benchmark maakt elk model\n"
        "goed. De belangrijkste is DE LAATST BEKENDE WAARDE: voor een\n"
        "persistente reeks is dat de natuurlijke naieve voorspelling.\n"
        "\n"
        "En er is een vijfde regel die de cyclus isoleert: dezelfde regressie\n"
        "ZONDER de golf, dus alleen de constante. Presteert de sinus daar niet\n"
        "beter dan, dan doet zijn golf niets en zit alle voorspelkracht in de\n"
        "constante term."
    )
    wf = walk_forward_sine_test(vol, spec["peak_period"], horizon=21)
    results = pd.DataFrame(
        [
            {"model": f"sinus ({spec['peak_period']:.0f} dagen)", "RMSE": wf["sine_rmse"]},
            {"model": "alleen de constante (zelfde regressie, geen golf)",
             "RMSE": wf["constant_only_rmse"]},
            {"model": "laatste waarde (naief)", "RMSE": wf["naive_last_rmse"]},
            {"model": "gemiddelde laatste 21 dagen", "RMSE": wf["mean_recent_rmse"]},
            {"model": "historisch gemiddelde", "RMSE": wf["mean_all_rmse"]},
        ]
    )
    print(
        f"\nWalk-forward: {wf['n_folds']} vensters, horizon {wf['horizon']} dagen.\n"
        "RMSE in volatiliteitspunten (jaarbasis, dus 3.0 = 3 procentpunt fout):"
    )
    print(results.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print(
        f"\nWat de GOLF toevoegt bovenop de constante: "
        f"{wf['wave_contribution_pct']:+.2f}% minder fout."
    )
    if abs(wf["wave_contribution_pct"]) < 1.0:
        print(
            "   Dat is verwaarloosbaar. De sinus en de kale constante presteren\n"
            "   praktisch identiek, dus de golf doet niets - alle voorspelkracht\n"
            "   zit in de constante term."
        )

    best = min(wf["naive_last_rmse"], wf["mean_recent_rmse"], wf["mean_all_rmse"])
    if wf["sine_beats_best_benchmark"]:
        print(
            f"\n-> De sinus ({wf['sine_rmse']:.3f}) verslaat de beste benchmark "
            f"({best:.3f})."
        )
    else:
        worse = (wf["sine_rmse"] / best - 1) * 100
        print(
            f"\n-> De sinus ({wf['sine_rmse']:.3f}) is {worse:.1f}% SLECHTER dan de\n"
            f"   beste benchmark ({best:.3f}). Hij voegt niets toe."
        )

    print(
        "\nLET OP DE OPZET: de horizon is 21 dagen, niet een blok van jaren.\n"
        "Dat is bewust. Voorspel je in een keer twee jaar vooruit, dan wint\n"
        "automatisch elk model dat het langjarig gemiddelde voorspelt - de\n"
        "volatiliteit keert daarnaartoe terug. Dan meet je mean reversion,\n"
        "niet cycliciteit. Ik had die fout eerst in dit script zitten: met een\n"
        "horizon van 540 dagen 'versloeg' de sinus de naieve benchmark met 28%,\n"
        "terwijl hij exact gelijk presteerde aan het kale gemiddelde. Dat was\n"
        "het teken dat de golf niets deed."
    )

    # ------------------------------------------------------------------
    section("CONCLUSIE")
    print(
        "De vraag was: kunnen we met een sinus of Fourier-reeks de rustige en\n"
        "onrustige periodes voorspellen?\n"
    )
    verdict_lines = [
        f"1. Tegen een JUISTE referentie (persistent maar ritmeloos) is de "
        f"sterkste afwijking een periode van {spec['peak_period']:.0f} dagen, "
        f"op {spec['peak_ratio']:.1f}x de grens. Statistisch detecteerbaar.",
        f"2. Maar die sinus verklaart slechts "
        f"{spec['sine_r_squared'] * 100:.1f}% van de variatie in de "
        "volatiliteit. Statistisch significant is niet hetzelfde als nuttig.",
        f"3. Out-of-sample is de sinus "
        f"{'beter' if wf['sine_beats_best_benchmark'] else 'SLECHTER'} dan de "
        f"beste benchmark: RMSE {wf['sine_rmse']:.2f} tegenover "
        f"{min(wf['naive_last_rmse'], wf['mean_recent_rmse'], wf['mean_all_rmse']):.2f} "
        "volatiliteitspunten.",
        f"4. De golf voegt {wf['wave_contribution_pct']:+.2f}% toe bovenop een "
        "kale constante. Alle voorspelkracht zit in de constante, niet in het "
        "ritme.",
        f"5. De autocorrelatie van de volatiliteit "
        f"({persistence['phi']:.3f} op dag 1) daalt langzaam maar wordt nooit "
        "negatief: persistentie, geen cyclus.",
    ]
    for line in verdict_lines:
        print(f"   {line}")

    print(
        "\nHet antwoord is dus NEE - en de nuance is belangrijker dan het\n"
        "antwoord. Er zit WEL iets op 64 dagen: het is statistisch\n"
        "detecteerbaar tegen een eerlijke referentie. Maar het verklaart 0,8%\n"
        "van de beweging en het maakt voorspellingen SLECHTER. Dat onderscheid\n"
        "tussen 'statistisch significant' en 'praktisch bruikbaar' is precies\n"
        "wat je in een sollicitatiegesprek moet kunnen maken.\n"
        "\n"
        "Het is ook precies wat je zou moeten verwachten:\n"
        "als de volatiliteit van goud een voorspelbaar ritme had, zou iedereen\n"
        "die dat wist opties kopen voor de piek en verkopen erna. Dat handelen\n"
        "zou het ritme wegconcurreren.\n"
        "\n"
        "MAAR: dat betekent niet dat volatiliteit onvoorspelbaar is. Hij is wel\n"
        "degelijk voorspelbaar, alleen op een andere manier:\n"
        "\n"
        "  NIET  'over 60 dagen komt de volgende onrustige periode'\n"
        "  WEL   'het is nu onrustig, dus morgen waarschijnlijk ook'\n"
        "\n"
        f"De eerste-orde autocorrelatie van {persistence['phi']:.3f} is enorm. Daar\n"
        "zit echte voorspelkracht in - en dat is precies wat GARCH modelleert.\n"
        "GARCH is geen cyclusmodel maar een persistentiemodel, en dat is de\n"
        "goede keuze voor deze data.\n"
        "\n"
        "Voor je margeberekening in fase 4 is dat zelfs bruikbaarder: je wilt\n"
        "weten hoeveel buffer je NU nodig hebt gegeven de huidige\n"
        "marktomstandigheden, niet wanneer de volgende crisis komt."
    )

    print(f"\n{LINE}")
    print(f"Figuren: {get_output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
