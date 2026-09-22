"""Figuren voor fase 4: gesimuleerde paden en de margebehoefte.

Een fan chart is de natuurlijke visualisatie van een simulatie: niet één lijn
maar een band van mogelijke uitkomsten. Dat sluit aan bij wat het project
belooft — een kansverdeling, geen puntvoorspelling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from goldmodel.viz.style import COLORS, ROLE, annotate, save_figure


def plot_fan_chart(
    paths_sample: np.ndarray,
    percentile_bands: dict[str, np.ndarray],
    *,
    spot_price: float,
    title: str,
    filename: str,
):
    """Fan chart: de band van mogelijke prijspaden.

    Argumenten:
        paths_sample: Een kleine selectie individuele paden (n x dagen+1),
            als cumulatieve log-rendementen.
        percentile_bands: Per label een array met het percentiel per dag.
        spot_price: De startprijs, om de y-as in dollars te zetten.
    """
    fig, (ax_paths, ax_band) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    days = np.arange(paths_sample.shape[1])

    # -- links: individuele paden ---------------------------------------
    for row in paths_sample:
        ax_paths.plot(
            days,
            spot_price * np.exp(row),
            color=ROLE["empirical"],
            linewidth=0.7,
            alpha=0.35,
        )
    ax_paths.axhline(spot_price, color=ROLE["ink_soft"], linewidth=1.2, linestyle="--")
    ax_paths.set_xlabel("Handelsdagen vooruit")
    ax_paths.set_ylabel("Goudprijs (USD)")
    ax_paths.set_title(
        f"{paths_sample.shape[0]} van de gesimuleerde paden", fontsize=11
    )
    annotate(
        ax_paths,
        "Elk pad is toeval.\n\n"
        "De simulatie voorspelt niet\n"
        "WAAR de prijs heen gaat -\n"
        "alleen hoe groot de spreiding\n"
        "van de mogelijkheden is.",
        loc="upper left",
    )

    # -- rechts: de percentielband --------------------------------------
    labels = list(percentile_bands.keys())
    median = percentile_bands.get("p50")

    # Van buiten naar binnen inkleuren, zodat de donkerste band het
    # middengebied is.
    band_pairs = [("p1", "p99"), ("p5", "p95"), ("p25", "p75")]
    alphas = (0.15, 0.25, 0.40)
    for (lower, upper), alpha in zip(band_pairs, alphas):
        if lower in percentile_bands and upper in percentile_bands:
            ax_band.fill_between(
                days,
                spot_price * np.exp(percentile_bands[lower]),
                spot_price * np.exp(percentile_bands[upper]),
                color=ROLE["empirical"],
                alpha=alpha,
                linewidth=0,
            )

    if median is not None:
        ax_band.plot(
            days,
            spot_price * np.exp(median),
            color=ROLE["highlight"],
            linewidth=2.0,
            label="mediaan",
        )
    ax_band.axhline(
        spot_price,
        color=ROLE["ink_soft"],
        linewidth=1.2,
        linestyle="--",
        label=f"nu: ${spot_price:,.0f}",
    )
    ax_band.set_xlabel("Handelsdagen vooruit")
    ax_band.set_ylabel("Goudprijs (USD)")
    ax_band.set_title("De verdeling van uitkomsten", fontsize=11)
    ax_band.legend(loc="upper left", fontsize=8.5)
    annotate(
        ax_band,
        "De banden zijn 50%, 90% en\n"
        "98% van de uitkomsten.\n\n"
        "Dit is het antwoord van het\n"
        "project: een verdeling, geen\n"
        "enkel getal.",
        loc="lower left",
    )

    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename)


def plot_model_comparison(
    results: dict[str, np.ndarray],
    historical: np.ndarray,
    *,
    filename: str = "20_modellen_vergeleken.png",
):
    """Vergelijkt de verdeling van de tegenbeweging per model met de historie.

    Dit is de eerlijkheidsfiguur van fase 4: de simulaties naast wat er echt
    gebeurde, zodat zichtbaar is welk model de staart over- of onderschat.
    """
    fig, (ax_dist, ax_tail) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    palette = [COLORS["blue"], COLORS["orange"], COLORS["aqua"]]

    # -- links: de hele verdeling ---------------------------------------
    bins = np.linspace(0, 0.6, 70)
    ax_dist.hist(
        historical,
        bins=bins,
        density=True,
        color=ROLE["reference"],
        alpha=0.55,
        label=f"historisch (n={len(historical)})",
    )
    for index, (name, values) in enumerate(results.items()):
        ax_dist.hist(
            values,
            bins=bins,
            density=True,
            histtype="step",
            linewidth=2.0,
            color=palette[index % len(palette)],
            label=name,
        )
    ax_dist.set_xlabel("Grootste tussentijdse tegenbeweging")
    ax_dist.set_ylabel("Dichtheid")
    ax_dist.set_title("De hele verdeling", fontsize=11)
    ax_dist.legend(loc="upper right", fontsize=8.5)

    # -- rechts: alleen de staart, waar het om gaat ---------------------
    levels = np.array([50, 75, 90, 95, 99, 99.5])
    positions = np.arange(len(levels))
    width = 0.8 / (len(results) + 1)

    historical_values = [np.percentile(historical, level) * 100 for level in levels]
    ax_tail.bar(
        positions - 0.4 + width / 2,
        historical_values,
        width,
        color=ROLE["reference"],
        label="historisch",
    )
    for index, (name, values) in enumerate(results.items()):
        simulated = [np.percentile(values, level) * 100 for level in levels]
        ax_tail.bar(
            positions - 0.4 + width * (index + 1.5),
            simulated,
            width,
            color=palette[index % len(palette)],
            label=name,
        )

    ax_tail.set_xticks(positions)
    ax_tail.set_xticklabels([f"p{level:g}" for level in levels])
    ax_tail.set_xlabel("Percentiel")
    ax_tail.set_ylabel("Tegenbeweging (%)")
    ax_tail.set_title("Per percentiel: klopt de staart?", fontsize=11)
    ax_tail.legend(loc="upper left", fontsize=8.5)
    annotate(
        ax_tail,
        "Bij p99 zie je het verschil:\n"
        "de constante modellen komen\n"
        "te laag uit, GARCH te hoog.\n\n"
        "De historie zit ertussen.",
        loc="lower right",
    )

    fig.suptitle(
        "Simulatie tegenover werkelijkheid: welk model heeft de staart goed?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename)


def plot_buffer_curve(
    max_adverse: np.ndarray,
    *,
    notional: float,
    current_rule: tuple[float, float] = (0.05, 0.10),
    filename: str = "21_buffercurve.png",
):
    """De buffer als functie van het gewenste zekerheidsniveau.

    Dit is de figuur die de oorspronkelijke vraag beantwoordt, en hij maakt
    de afweging zichtbaar: meer zekerheid kost steil oplopend kapitaal.
    """
    fig, (ax_curve, ax_coverage) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    # -- links: buffer tegen zekerheid ----------------------------------
    confidences = np.linspace(0.50, 0.999, 200)
    buffers = np.array(
        [np.percentile(max_adverse, level * 100) for level in confidences]
    )

    ax_curve.plot(
        confidences * 100, buffers * 100, color=ROLE["empirical"], linewidth=2.4
    )

    for rule, style in zip(current_rule, ("--", ":")):
        ax_curve.axhline(
            rule * 100,
            color=ROLE["theoretical"],
            linestyle=style,
            linewidth=1.6,
        )
        coverage = float((max_adverse <= rule).mean())
        # Label rechts van het midden plaatsen: linksonder loopt de curve
        # zelf door dat gebied en overlapt de tekst.
        ax_curve.annotate(
            f"{rule:.0%}-regel dekt {coverage:.0%} van de paden",
            xy=(70, rule * 100),
            xytext=(70, rule * 100 - 2.2),
            fontsize=8.5,
            color=ROLE["theoretical"],
        )

    for level in (0.95, 0.99):
        value = float(np.percentile(max_adverse, level * 100))
        ax_curve.plot([level * 100], [value * 100], "o", color=ROLE["highlight"])
        ax_curve.annotate(
            f"{level:.0%}: {value * 100:.1f}%",
            xy=(level * 100, value * 100),
            xytext=(-60, 8),
            textcoords="offset points",
            fontsize=9,
            color=ROLE["highlight"],
        )

    ax_curve.set_xlabel("Gewenste zekerheid (%)")
    ax_curve.set_ylabel("Benodigde buffer (% van notioneel)")
    ax_curve.set_title("Meer zekerheid kost steil meer kapitaal", fontsize=11)

    # -- rechts: wat elke buffer dekt -----------------------------------
    buffer_levels = np.linspace(0.0, 0.5, 200)
    coverage = np.array([(max_adverse <= level).mean() for level in buffer_levels])

    ax_coverage.plot(
        buffer_levels * 100, coverage * 100, color=ROLE["secondary"], linewidth=2.4
    )
    for rule in current_rule:
        covered = float((max_adverse <= rule).mean())
        ax_coverage.plot([rule * 100], [covered * 100], "o", color=ROLE["theoretical"])
        ax_coverage.annotate(
            f"{rule:.0%} -> {covered:.0%}",
            xy=(rule * 100, covered * 100),
            xytext=(8, -12),
            textcoords="offset points",
            fontsize=9,
            color=ROLE["theoretical"],
        )
    ax_coverage.axhline(99, color=ROLE["highlight"], linestyle="--", linewidth=1.4)
    ax_coverage.text(
        1, 96.5, "99%-doel", fontsize=8.5, color=ROLE["highlight"]
    )
    ax_coverage.set_xlabel("Aangehouden buffer (% van notioneel)")
    ax_coverage.set_ylabel("Aandeel paden gedekt (%)")
    ax_coverage.set_title("Wat dekt een gegeven buffer?", fontsize=11)
    ax_coverage.set_ylim(0, 102)

    annotate(
        ax_coverage,
        f"Notioneel: ${notional:,.0f}\n"
        "per contract van 100 ounce.\n\n"
        "Lees hier af wat jouw huidige\n"
        "vuistregel werkelijk dekt.",
        loc="lower right",
    )

    fig.suptitle(
        "De margebuffer: hoeveel zekerheid wil je, en wat kost die?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename)


def plot_kupiec_results(
    results: pd.DataFrame, *, filename: str = "22_kupiec_validatie.png"
):
    """Toont de backtest-uitkomsten per horizon en model.

    De belangrijkste figuur van fase 4: hij laat zien welk model de toets
    haalt wanneer die toets genoeg vensters heeft om iets te kunnen zeggen.
    """
    fig, (ax_counts, ax_power) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    horizons = sorted(results["horizon"].unique())
    models = list(results["model"].unique())
    palette = [COLORS["blue"], COLORS["orange"], COLORS["aqua"]]
    width = 0.8 / (len(models) + 1)
    positions = np.arange(len(horizons))

    # -- links: overschrijdingen tegenover verwacht ---------------------
    expected = [
        float(results[results["horizon"] == h]["expected"].iloc[0]) for h in horizons
    ]
    ax_counts.bar(
        positions - 0.4 + width / 2,
        expected,
        width,
        color=ROLE["reference"],
        label="verwacht bij 99%",
    )
    for index, model in enumerate(models):
        subset = results[results["model"] == model].set_index("horizon")
        values = [float(subset.loc[h, "exceedances"]) for h in horizons]
        ax_counts.bar(
            positions - 0.4 + width * (index + 1.5),
            values,
            width,
            color=palette[index % len(palette)],
            label=model,
        )

    ax_counts.set_xticks(positions)
    ax_counts.set_xticklabels([f"{h} dagen" for h in horizons])
    ax_counts.set_ylabel("Aantal VaR-overschrijdingen")
    ax_counts.set_title("Waargenomen tegenover verwacht", fontsize=11)
    ax_counts.legend(loc="upper left", fontsize=8.5)

    # -- rechts: p-waarden ----------------------------------------------
    # Overlappende lijnen krijgen een eigen stijl en een kleine verschuiving,
    # anders verdwijnt een model volledig achter een ander waar de p-waarden
    # samenvallen.
    styles = ("o-", "s--", "^-")
    for index, model in enumerate(models):
        subset = results[results["model"] == model].set_index("horizon")
        values = [float(subset.loc[h, "p_value"]) for h in horizons]
        ax_power.plot(
            positions + (index - 1) * 0.03,
            values,
            styles[index % len(styles)],
            color=palette[index % len(palette)],
            linewidth=2.0,
            markersize=7,
            label=model,
        )

    ax_power.axhline(0.05, color=ROLE["highlight"], linestyle="--", linewidth=1.6)
    ax_power.text(
        len(horizons) - 1.4,
        0.075,
        "onder deze lijn: model VERWORPEN",
        fontsize=8.5,
        color=ROLE["highlight"],
    )
    ax_power.set_xticks(positions)
    ax_power.set_xticklabels([f"{h} dagen" for h in horizons])
    ax_power.set_ylabel("p-waarde Kupiec-toets")
    ax_power.set_title("Haalt het model de toets?", fontsize=11)
    ax_power.set_ylim(0, 1.05)
    ax_power.legend(loc="upper left", fontsize=8.5)

    annotate(
        ax_power,
        "Alle drie de modellen blijven\n"
        "boven de lijn: geen enkel model\n"
        "wordt verworpen.\n\n"
        "Maar de toets is hier ZWAK. Zelfs\n"
        "bij 495 vensters verwacht je maar\n"
        "5 overschrijdingen, en 5 tegen 9\n"
        "is statistisch niet hard te maken.\n\n"
        "Kijk daarom ook naar het linker\n"
        "paneel: GARCH zit het dichtst bij\n"
        "het verwachte aantal.",
        loc="lower left",
    )

    fig.suptitle(
        "Kupiec-validatie: belooft het model 99% en levert het dat ook?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename)
