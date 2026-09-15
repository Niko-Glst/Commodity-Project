"""Uitlegfiguren: bedoeld om één begrip te verduidelijken, niet om te meten.

De figuren in ``distributions.py`` tonen wat de data zegt. Deze tonen wat een
begrip betekent, met eenvoudige voorbeelden en waar nuttig verzonnen getallen.
Dat onderscheid is bewust: een uitlegfiguur mag versimpelen, een resultaatfiguur
niet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import stats as sps

from goldmodel.viz.style import ROLE, annotate, save_figure


def plot_qq_explained(filename: str = "10_qq_uitgelegd.png"):
    """Legt uit wat de rechte lijn in een QQ-plot betekent.

    Opbouw in vier panelen, van het simpelste geval naar het echte:

    1. Data die WEL normaal is: de punten liggen op de lijn.
    2. Hoe de plot gemaakt wordt: sorteren en tegen elkaar uitzetten.
    3. Data met dikke staarten: de punten buigen weg aan de uiteinden.
    4. Wat de afwijking betekent in gewone taal.
    """
    rng = np.random.default_rng(42)
    n = 500

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    ax_normal, ax_how = axes[0]
    ax_fat, ax_meaning = axes[1]

    # -- 1. Data die echt normaal is -----------------------------------
    normal_sample = rng.standard_normal(n)
    theoretical, ordered = sps.probplot(normal_sample, dist="norm", fit=False)

    ax_normal.scatter(theoretical, ordered, s=14, color=ROLE["empirical"], alpha=0.7)
    limits = np.array([-3.5, 3.5])
    ax_normal.plot(
        limits, limits, color=ROLE["reference"], linestyle="--", linewidth=1.8
    )
    ax_normal.set_xlim(-3.5, 3.5)
    ax_normal.set_ylim(-3.5, 3.5)
    ax_normal.set_xlabel("Wat de normale verdeling voorspelt")
    ax_normal.set_ylabel("Wat we waarnemen")
    ax_normal.set_title("1. Data die ÉCHT normaal verdeeld is", fontsize=11)
    annotate(
        ax_normal,
        "De punten liggen OP de lijn.\n\n"
        "De lijn is geen model dat we\n"
        "erdoorheen passen — hij zegt:\n"
        "'hier zouden de punten liggen\n"
        "als de verdeling perfect klopte'.",
        loc="upper left",
    )

    # -- 2. Hoe de plot tot stand komt ----------------------------------
    small = np.sort(rng.standard_normal(9))
    positions = (np.arange(1, 10) - 0.5) / 9
    expected = sps.norm.ppf(positions)

    ax_how.scatter(expected, small, s=90, color=ROLE["empirical"], zorder=5)
    for x, y, pct in zip(expected, small, positions):
        ax_how.annotate(
            f"{pct:.0%}",
            xy=(x, y),
            xytext=(0, 11),
            textcoords="offset points",
            fontsize=8,
            ha="center",
            color=ROLE["ink_soft"],
        )
    ax_how.plot(limits, limits, color=ROLE["reference"], linestyle="--", linewidth=1.8)
    ax_how.set_xlim(-2.5, 2.5)
    # Bovengrens ruimer dan de data zodat het percentagelabel boven het
    # hoogste punt niet tegen de titel aanloopt.
    ax_how.set_ylim(-2.5, 3.2)
    ax_how.set_xlabel("Verwachte waarde op die positie")
    ax_how.set_ylabel("Werkelijke waarde op die positie")
    ax_how.set_title("2. Hoe de plot gemaakt wordt (9 waarnemingen)", fontsize=11)
    annotate(
        ax_how,
        "Sorteer de waarnemingen van laag\n"
        "naar hoog. De kleinste van 9 hoort\n"
        "rond het 6%-punt te liggen, de\n"
        "middelste rond 50%, enzovoort.\n\n"
        "Zet werkelijk tegen verwacht uit:\n"
        "klopt het, dan ligt alles op de lijn.",
        loc="upper left",
    )

    # -- 3. Data met dikke staarten -------------------------------------
    fat_sample = rng.standard_t(df=3, size=n)
    fat_sample = fat_sample / fat_sample.std()
    theoretical_fat, ordered_fat = sps.probplot(fat_sample, dist="norm", fit=False)

    ax_fat.scatter(
        theoretical_fat, ordered_fat, s=14, color=ROLE["highlight"], alpha=0.7
    )
    ax_fat.plot(limits, limits, color=ROLE["reference"], linestyle="--", linewidth=1.8)
    ax_fat.set_xlim(-3.5, 3.5)
    # Y-as begrenzen op het 1e/99e percentiel plus wat lucht. Zonder dat
    # rekt één extreme uitschieter de as zo ver op dat de S-vorm - juist
    # datgene wat deze figuur moet laten zien - visueel verdwijnt.
    span = float(np.percentile(np.abs(ordered_fat), 99)) * 1.5
    ax_fat.set_ylim(-span, span)
    ax_fat.set_xlabel("Wat de normale verdeling voorspelt")
    ax_fat.set_ylabel("Wat we waarnemen")
    ax_fat.set_title("3. Data met dikke staarten (zoals goud)", fontsize=11)

    # Markeer de twee uiteinden. We kiezen punten die binnen het zichtbare
    # bereik vallen (rond het 2e en 98e percentiel), niet de allerextreemste:
    # die liggen na het begrenzen van de as buiten beeld.
    low_index = int(len(ordered_fat) * 0.02)
    high_index = int(len(ordered_fat) * 0.98)

    ax_fat.annotate(
        "hier is de werkelijkheid\nERGER dan voorspeld",
        xy=(theoretical_fat[low_index], ordered_fat[low_index]),
        xytext=(-0.3, -span * 0.72),
        fontsize=8.5,
        color=ROLE["highlight"],
        ha="center",
        arrowprops={"arrowstyle": "->", "color": ROLE["highlight"], "linewidth": 1.2},
    )
    ax_fat.annotate(
        "en hier ook",
        xy=(theoretical_fat[high_index], ordered_fat[high_index]),
        xytext=(0.3, span * 0.78),
        fontsize=8.5,
        color=ROLE["highlight"],
        ha="center",
        arrowprops={"arrowstyle": "->", "color": ROLE["highlight"], "linewidth": 1.2},
    )

    # -- 4. Wat dat betekent --------------------------------------------
    ax_meaning.axis("off")
    ax_meaning.set_title("4. Wat de afwijking betekent", fontsize=11)
    ax_meaning.text(
        0.02,
        0.95,
        "De lijn = 'perfect normaal'\n"
        "─────────────────────────────\n\n"
        "PUNTEN OP DE LIJN\n"
        "   De verdeling klopt.\n\n"
        "LINKSONDER ONDER DE LIJN\n"
        "   De slechtste dagen zijn SLECHTER\n"
        "   dan de normale verdeling voorspelt.\n"
        "   → je verliest meer dan verwacht\n\n"
        "RECHTSBOVEN BOVEN DE LIJN\n"
        "   De beste dagen zijn BETER dan\n"
        "   voorspeld.\n\n"
        "SAMEN: een liggende S-vorm.\n"
        "   Dat is de handtekening van\n"
        "   dikke staarten.\n\n"
        "Voor jouw margevraag telt vooral de\n"
        "linkeronderhoek: daar zitten de dagen\n"
        "die een margin call veroorzaken.",
        transform=ax_meaning.transAxes,
        fontsize=9.5,
        va="top",
        family="monospace",
        linespacing=1.5,
        color=ROLE["ink"],
    )

    fig.suptitle(
        "Wat betekent de rechte lijn in een QQ-plot?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


def plot_t_versus_normal(filename: str = "11_t_versus_normaal.png"):
    """Vergelijkt de t-verdeling met de normale verdeling.

    Het verschil zit volledig in de staarten. In het midden lijken ze sterk
    op elkaar; pas bij de extremen loopt het uiteen, en precies daar gaat een
    margeberekening over.
    """
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    ax_shape, ax_tail = axes[0]
    ax_df, ax_table = axes[1]

    x = np.linspace(-5, 5, 600)
    normal_pdf = sps.norm.pdf(x)

    # -- 1. De vormen naast elkaar --------------------------------------
    ax_shape.plot(
        x, normal_pdf, color=ROLE["theoretical"], linewidth=2.4, label="normale verdeling"
    )
    ax_shape.plot(
        x,
        sps.t.pdf(x, df=4),
        color=ROLE["empirical"],
        linewidth=2.4,
        label="t-verdeling (4 vrijheidsgraden)",
    )
    ax_shape.set_xlabel("Standaardafwijkingen van het gemiddelde")
    ax_shape.set_ylabel("Kans op deze waarde")
    ax_shape.set_title("1. In het midden lijken ze sterk op elkaar", fontsize=11)
    ax_shape.legend(loc="upper right", fontsize=8.5)
    annotate(
        ax_shape,
        "Hier zie je nauwelijks verschil.\n"
        "Daarom moet je naar de staarten\n"
        "kijken (paneel 2).",
        loc="upper left",
    )

    # -- 2. Inzoomen op de staart ---------------------------------------
    x_tail = np.linspace(2.5, 6, 400)
    ax_tail.plot(
        x_tail,
        sps.norm.pdf(x_tail),
        color=ROLE["theoretical"],
        linewidth=2.4,
        label="normale verdeling",
    )
    ax_tail.plot(
        x_tail,
        sps.t.pdf(x_tail, df=4),
        color=ROLE["empirical"],
        linewidth=2.4,
        label="t-verdeling (df=4)",
    )
    ax_tail.fill_between(
        x_tail,
        sps.norm.pdf(x_tail),
        sps.t.pdf(x_tail, df=4),
        color=ROLE["empirical"],
        alpha=0.2,
    )
    ax_tail.set_yscale("log")
    ax_tail.set_xlabel("Standaardafwijkingen van het gemiddelde")
    ax_tail.set_ylabel("Kans (logaritmische schaal)")
    ax_tail.set_title("2. Ingezoomd op de staart: enorm verschil", fontsize=11)
    ax_tail.legend(loc="upper right", fontsize=8.5)

    ratio_4sd = sps.t.pdf(4, df=4) / sps.norm.pdf(4)
    annotate(
        ax_tail,
        f"Bij 4 standaardafwijkingen is de\n"
        f"t-verdeling {ratio_4sd:.0f}x waarschijnlijker\n"
        "dan de normale.\n\n"
        "Het blauwe vlak is het verschil:\n"
        "het staartrisico dat de normale\n"
        "verdeling niet ziet.",
        loc="lower left",
    )

    # -- 3. Wat de vrijheidsgraden doen ---------------------------------
    for df, colour, style in (
        (2, ROLE["highlight"], "-"),
        (4, ROLE["empirical"], "-"),
        (10, ROLE["secondary"], "-"),
        (30, ROLE["reference"], ":"),
    ):
        ax_df.plot(
            x,
            sps.t.pdf(x, df=df),
            color=colour,
            linewidth=2.0,
            linestyle=style,
            label=f"t met df={df}",
        )
    ax_df.plot(
        x,
        normal_pdf,
        color=ROLE["theoretical"],
        linewidth=2.4,
        linestyle="--",
        label="normaal",
    )
    ax_df.set_xlim(-5, 5)
    ax_df.set_xlabel("Standaardafwijkingen van het gemiddelde")
    ax_df.set_ylabel("Kans op deze waarde")
    ax_df.set_title("3. Vrijheidsgraden regelen hoe dik de staarten zijn", fontsize=11)
    ax_df.legend(loc="upper right", fontsize=8)
    annotate(
        ax_df,
        "Weinig vrijheidsgraden\n"
        "= dikke staarten.\n\n"
        "Boven ongeveer 30 is de\n"
        "t-verdeling niet meer van\n"
        "de normale te onderscheiden.\n\n"
        "Goud zit op 3,6.",
        loc="upper left",
    )

    # -- 4. De getallen die ertoe doen ----------------------------------
    ax_table.axis("off")
    ax_table.set_title("4. Hoe vaak komt een extreme dag voor?", fontsize=11)

    rows = []
    for sd in (2, 3, 4, 5):
        p_normal = 2 * (1 - sps.norm.cdf(sd))
        p_t = 2 * (1 - sps.t.cdf(sd, df=3.6))
        rows.append(
            (
                f"{sd} sd",
                f"1 op {1 / p_normal:>9,.0f}",
                f"1 op {1 / p_t:>7,.0f}",
                f"{p_t / p_normal:>6.0f}x",
            )
        )

    text = (
        "Kans op een beweging groter dan:\n"
        "────────────────────────────────────────────────\n"
        f"{'':6s} {'normale verd.':>16s} {'t (df=3,6)':>14s} {'factor':>8s}\n"
        "────────────────────────────────────────────────\n"
    )
    for row in rows:
        text += f"{row[0]:6s} {row[1]:>16s} {row[2]:>14s} {row[3]:>8s}\n"

    text += (
        "\n(in handelsdagen; een jaar heeft er 252)\n\n"
        "Lees de laatste regel goed:\n"
        "Een 5-sd-dag is volgens de normale\n"
        "verdeling een gebeurtenis van eens in de\n"
        "1,7 miljoen dagen - oftewel eens in de\n"
        "7000 jaar. Volgens de t-verdeling gebeurt\n"
        "hij eens in de 102 dagen.\n\n"
        "HET SCHERPSTE VOORBEELD\n"
        "Op 30-01-2026 daalde goud 10,8%.\n"
        "Dat is 9,9 standaardafwijkingen.\n\n"
        "Onder de normale verdeling is de kans\n"
        "daarop 1 op 59.000.000.000.000.000.000.000\n"
        "dagen. Het heelal bestaat pas 5 biljoen\n"
        "dagen.\n\n"
        "De normale verdeling zegt dus: dit kan\n"
        "niet. Het gebeurde vorig jaar."
    )

    ax_table.text(
        0.02,
        0.95,
        text,
        transform=ax_table.transAxes,
        fontsize=9,
        va="top",
        family="monospace",
        linespacing=1.45,
        color=ROLE["ink"],
    )

    fig.suptitle(
        "Wat is het verschil tussen de t-verdeling en de normale verdeling?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


def plot_margin_rule(
    returns: pd.Series,
    spot_price: float,
    *,
    filename: str = "12_margeregel.png",
):
    """Zet de 5-10%-vuistregel af tegen wat de data zegt.

    Toont voor verschillende horizonnen welk verlies je met 99% zekerheid niet
    overschrijdt, en waar de vuistregel dan ligt.
    """
    horizons = [1, 5, 10, 21, 63]
    labels = ["1 dag", "1 week", "2 weken", "1 maand", "1 kwartaal"]

    p99_losses = []
    worst_losses = []
    for days in horizons:
        cumulative = np.exp(returns.rolling(days).sum()) - 1
        cumulative = cumulative.dropna()
        # Short positie: verlies bij STIJGING van de prijs.
        p99_losses.append(float(np.percentile(cumulative, 99)) * 100)
        worst_losses.append(float(cumulative.max()) * 100)

    fig, (ax_bars, ax_text) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    positions = np.arange(len(horizons))
    width = 0.38

    bars_p99 = ax_bars.bar(
        positions - width / 2,
        p99_losses,
        width,
        color=ROLE["empirical"],
        label="99%-verlies (1 op 100 is erger)",
    )
    bars_worst = ax_bars.bar(
        positions + width / 2,
        worst_losses,
        width,
        color=ROLE["highlight"],
        label="ergste in 23 jaar",
    )

    for bar in list(bars_p99) + list(bars_worst):
        ax_bars.annotate(
            f"{bar.get_height():.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
            color=ROLE["ink_soft"],
        )

    ax_bars.axhspan(5, 10, color=ROLE["theoretical"], alpha=0.18)
    ax_bars.axhline(5, color=ROLE["theoretical"], linewidth=1.4, linestyle="--")
    ax_bars.axhline(10, color=ROLE["theoretical"], linewidth=1.4, linestyle="--")
    ax_bars.text(
        len(horizons) - 0.4,
        7.5,
        "vuistregel 5-10%",
        fontsize=9,
        color=ROLE["theoretical"],
        ha="right",
        va="center",
    )

    ax_bars.set_xticks(positions)
    ax_bars.set_xticklabels(labels)
    ax_bars.set_ylabel("Prijsstijging in procenten (= verlies op een short)")
    ax_bars.set_title(
        "Hoeveel kan de goudprijs tegen je in bewegen?", fontsize=11
    )
    ax_bars.legend(loc="upper left", fontsize=8.5)

    # -- rechts: de uitleg ----------------------------------------------
    ax_text.axis("off")
    ax_text.set_title("Waar de vuistregel vandaan komt", fontsize=11)

    contract_value = spot_price * 100
    text = (
        "EEN COMEX-GOUDCONTRACT\n"
        "─────────────────────────────────────\n"
        f"  100 troy ounce x ${spot_price:,.2f}\n"
        f"  = ${contract_value:,.0f} notionele waarde\n\n"
        "DE BEURS VRAAGT ONGEVEER 5%\n"
        "  Dat is de 'initial margin': het bedrag\n"
        "  dat je moet storten om te mogen\n"
        "  handelen. De beurs kiest dat zo dat\n"
        "  het ongeveer de ergste dag van\n"
        "  gisteren dekt.\n\n"
        "DAAR KOMT DE 5% VANDAAN.\n"
        "  Het is geen risicomodel maar een\n"
        "  beursvereiste, afgeleid van korte-\n"
        "  termijn volatiliteit.\n\n"
        "EN DE 10%?\n"
        "  Een veiligheidsmarge erbovenop, zodat\n"
        "  je niet bij de eerste tegenbeweging\n"
        "  moet bijstorten.\n\n"
        "HET PROBLEEM\n"
        "  Beide getallen staan VAST. Ze bewegen\n"
        "  niet mee met de markt, terwijl de\n"
        "  volatiliteit dat wel doet - en\n"
        "  voorspelbaar is (bevinding 3).\n\n"
        "  In een rustige markt houd je te veel\n"
        "  kapitaal vast. In een crisis te weinig."
    )
    ax_text.text(
        0.02,
        0.97,
        text,
        transform=ax_text.transAxes,
        fontsize=9,
        va="top",
        family="monospace",
        linespacing=1.4,
        color=ROLE["ink"],
    )

    fig.suptitle(
        "De 5-10%-vuistregel tegenover de data",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename), {
        "p99_by_horizon": dict(zip(labels, p99_losses)),
        "worst_by_horizon": dict(zip(labels, worst_losses)),
        "contract_value": contract_value,
    }
