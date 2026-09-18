"""Correlaties tussen goud en de macro-drivers, en hun stabiliteit.

Fase 2 stap 2. De vraag: welke drivers bewegen samen met goud, en is dat
verband stabiel door de tijd?

Waarom die tweede vraag net zo belangrijk is als de eerste
--------------------------------------------------------
Een gemiddelde correlatie over 23 jaar kan twee heel verschillende dingen
verbergen. Een stabiele correlatie van 0,3 is bruikbaar: je kunt erop rekenen.
Een correlatie die tussen −0,5 en +0,5 heen en weer slingert heeft óók een
gemiddelde rond nul, maar betekent iets volstrekt anders — dan is er geen
verband waar je een model op bouwt, alleen een reeks periodes met steeds een
ander regime.

Voor een hedge is dat onderscheid essentieel. Een hedge die "gemiddeld" werkt
maar wegvalt in een crisis, is precies dan waardeloos wanneer je hem nodig
hebt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from goldmodel.viz.style import COLORS, ROLE, annotate, save_figure

# Transformatie per reeks: rendement voor prijzen, verschil voor rentes.
RETURN_SERIES = frozenset(
    {"gold_futures", "silver_futures", "sp500", "dxy", "usd_broad_index"}
)


def build_change_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Zet het paneel om naar stationaire veranderingen.

    Prijsreeksen worden log-rendementen, rentes en spreads eerste verschillen.
    Welke transformatie per reeks hoort, volgt uit de stationariteitstoetsen
    van stap 1 — daar bleek dat alle twaalf reeksen na deze bewerking
    stationair zijn.
    """
    changes: dict[str, pd.Series] = {}
    for column in panel.columns:
        series = panel[column].dropna()
        if len(series) < 100:
            continue
        if column in RETURN_SERIES and (series > 0).all():
            changes[column] = np.log(series / series.shift(1))
        else:
            changes[column] = series.diff()
    frame = pd.DataFrame(changes)
    frame.index.name = "date"
    return frame


def correlations_with_gold(changes: pd.DataFrame) -> pd.DataFrame:
    """Correlatie van elke driver met het goudrendement, met context.

    Naast de correlatie geven we het aantal overlappende waarnemingen en een
    ruwe significantiegrens. Die grens is ongeveer 2/sqrt(n): daarbinnen is
    een correlatie niet van toeval te onderscheiden.
    """
    gold = changes["gold_futures"]
    rows = []
    for column in changes.columns:
        if column == "gold_futures":
            continue
        pair = pd.concat([gold, changes[column]], axis=1).dropna()
        if len(pair) < 200:
            continue
        correlation = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
        n = len(pair)
        bound = 1.96 / np.sqrt(n)
        rows.append(
            {
                "driver": column,
                "correlatie": correlation,
                "n": n,
                "toevalsgrens": bound,
                "significant": abs(correlation) > bound,
                "r_kwadraat_pct": correlation**2 * 100,
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("correlatie", key=abs, ascending=False)
        .reset_index(drop=True)
    )


def rolling_correlation(
    changes: pd.DataFrame, driver: str, *, window: int = 252
) -> pd.Series:
    """Voortschrijdende correlatie tussen goud en één driver.

    Een venster van 252 handelsdagen is ongeveer één jaar. Korter maakt de
    reeks onrustig door schattingsruis, langer smeert regimewisselingen uit.
    """
    pair = pd.concat([changes["gold_futures"], changes[driver]], axis=1).dropna()
    return pair.iloc[:, 0].rolling(window).corr(pair.iloc[:, 1]).dropna()


def stability_summary(changes: pd.DataFrame, drivers: list[str]) -> pd.DataFrame:
    """Vat samen hoe stabiel elke correlatie door de tijd is.

    De spreiding van de voortschrijdende correlatie is hier informatiever dan
    het gemiddelde: die vertelt of je met één getal kunt volstaan of niet.
    """
    rows = []
    for driver in drivers:
        if driver not in changes.columns:
            continue
        rolling = rolling_correlation(changes, driver)
        if rolling.empty:
            continue
        rows.append(
            {
                "driver": driver,
                "gemiddeld": float(rolling.mean()),
                "min": float(rolling.min()),
                "max": float(rolling.max()),
                "spreiding": float(rolling.max() - rolling.min()),
                "std": float(rolling.std()),
                "wisselt_teken": bool(rolling.min() < 0 < rolling.max()),
            }
        )
    return (
        pd.DataFrame(rows).sort_values("spreiding", ascending=False).reset_index(drop=True)
    )


# --------------------------------------------------------------------------
# Figuren
# --------------------------------------------------------------------------


def plot_correlation_overview(
    changes: pd.DataFrame, filename: str = "17_correlaties.png"
):
    """Welke drivers bewegen samen met goud, en hoeveel verklaart dat?"""
    table = correlations_with_gold(changes)

    fig, (ax_bars, ax_r2) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    labels = [d.replace("_", " ") for d in table["driver"]]
    positions = np.arange(len(labels))
    colours = [
        ROLE["empirical"] if significant else ROLE["reference"]
        for significant in table["significant"]
    ]

    ax_bars.barh(positions, table["correlatie"], color=colours, height=0.62)
    ax_bars.axvline(0, color=ROLE["ink_soft"], linewidth=1.0)

    # Toevalsgrenzen: daarbinnen is een correlatie niet te onderscheiden
    # van nul.
    mean_bound = float(table["toevalsgrens"].mean())
    for sign in (-1, 1):
        ax_bars.axvline(
            sign * mean_bound,
            color=ROLE["highlight"],
            linestyle=":",
            linewidth=1.4,
        )
    ax_bars.text(
        mean_bound * 1.15,
        len(labels) - 0.4,
        "grens van toeval",
        fontsize=8,
        color=ROLE["highlight"],
    )

    for i, value in enumerate(table["correlatie"]):
        offset = 0.012 if value >= 0 else -0.012
        ax_bars.annotate(
            f"{value:+.3f}",
            xy=(value + offset, i),
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=8.5,
            color=ROLE["ink_soft"],
        )

    ax_bars.set_yticks(positions)
    ax_bars.set_yticklabels(labels, fontsize=9)
    ax_bars.invert_yaxis()
    ax_bars.set_xlabel("Correlatie met het dagelijkse goudrendement")
    ax_bars.set_title("Welke drivers bewegen samen met goud?", fontsize=11)
    ax_bars.grid(axis="x", alpha=0.4)
    ax_bars.grid(axis="y", visible=False)

    # -- rechts: hoeveel verklaart dat eigenlijk? -----------------------
    ax_r2.barh(
        positions,
        table["r_kwadraat_pct"],
        color=ROLE["theoretical"],
        height=0.62,
    )
    for i, value in enumerate(table["r_kwadraat_pct"]):
        ax_r2.annotate(
            f"{value:.1f}%",
            xy=(value + 0.15, i),
            va="center",
            fontsize=8.5,
            color=ROLE["ink_soft"],
        )
    ax_r2.set_yticks(positions)
    ax_r2.set_yticklabels([])
    ax_r2.invert_yaxis()
    ax_r2.set_xlabel("Verklaarde variantie van goud (%)")
    ax_r2.set_title("Hoeveel verklaart elke driver los?", fontsize=11)
    ax_r2.grid(axis="x", alpha=0.4)
    ax_r2.grid(axis="y", visible=False)

    best = table.iloc[0]
    annotate(
        ax_r2,
        f"Zelfs de sterkste driver\n"
        f"({best['driver'].replace('_', ' ')}) verklaart\n"
        f"maar {best['r_kwadraat_pct']:.1f}% van de\n"
        "dagelijkse goudbeweging.\n\n"
        "De rest is ruis of iets dat\n"
        "we niet meten.",
        loc="lower right",
    )

    fig.suptitle(
        "Correlaties tussen goud en de macro-drivers (dagelijkse veranderingen)",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save_figure(fig, filename), table


def plot_rolling_correlations(
    changes: pd.DataFrame,
    drivers: list[str],
    *,
    filename: str = "18_rolling_correlaties.png",
):
    """Zijn de verbanden stabiel door de tijd?

    Elke driver krijgt een eigen paneel, want dat leest beter dan vier lijnen
    over elkaar — en het maakt de vergelijking met de nullijn per driver
    duidelijk.
    """
    available = [d for d in drivers if d in changes.columns]
    if not available:
        return None, pd.DataFrame()

    n_panels = len(available)
    fig, axes = plt.subplots(
        n_panels, 1, figsize=(13.5, 2.6 * n_panels), sharex=True
    )
    if n_panels == 1:
        axes = [axes]

    palette = [
        COLORS["blue"],
        COLORS["orange"],
        COLORS["aqua"],
        COLORS["violet"],
        COLORS["magenta"],
    ]

    crisis_windows = [
        ("2008-09-01", "2009-03-31", "financiële crisis"),
        ("2020-02-15", "2020-04-30", "covid-crash"),
    ]

    for index, (driver, ax) in enumerate(zip(available, axes)):
        rolling = rolling_correlation(changes, driver)
        full_period = float(
            pd.concat([changes["gold_futures"], changes[driver]], axis=1)
            .dropna()
            .corr()
            .iloc[0, 1]
        )

        ax.plot(
            rolling.index,
            rolling.values,
            color=palette[index % len(palette)],
            linewidth=1.5,
        )
        ax.axhline(0, color=ROLE["ink_soft"], linewidth=1.0)
        ax.axhline(
            full_period,
            color=ROLE["reference"],
            linestyle="--",
            linewidth=1.3,
            label=f"hele periode: {full_period:+.3f}",
        )

        for start, end, label in crisis_windows:
            ax.axvspan(
                pd.Timestamp(start),
                pd.Timestamp(end),
                color=ROLE["highlight"],
                alpha=0.12,
            )
            if index == 0:
                ax.text(
                    pd.Timestamp(start),
                    0.92,
                    f" {label}",
                    fontsize=7.5,
                    color=ROLE["highlight"],
                    va="top",
                )

        ax.set_ylim(-1, 1)
        ax.set_ylabel(driver.replace("_", "\n"), fontsize=9)
        ax.legend(loc="lower left", fontsize=8)
        ax.grid(axis="y", alpha=0.4)

    axes[-1].set_xlabel("Datum")
    fig.suptitle(
        "Rolling correlatie met goud (venster van 1 jaar): stabiel of niet?",
        fontsize=13,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path = save_figure(fig, filename)
    return path, stability_summary(changes, available)


def plot_driver_intercorrelations(
    changes: pd.DataFrame, filename: str = "19_drivers_onderling.png"
):
    """Correlaties tussen de drivers zelf: het multicollineariteitsprobleem.

    Twee drivers die sterk met elkaar correleren, bevatten dezelfde
    informatie. In een regressie kan het model dan niet uitmaken welke van
    de twee het werk doet, en worden de coëfficiënten onbetrouwbaar — grote
    standaardfouten, wisselende tekens bij kleine wijzigingen in de data.
    """
    drivers = [c for c in changes.columns if c != "gold_futures"]
    matrix = changes[drivers].corr()

    fig, ax = plt.subplots(figsize=(9.5, 8))

    # Diverging palet: rood-neutraal-blauw met grijs in het midden, want
    # het teken van een correlatie is inhoudelijk relevant.
    image = ax.imshow(matrix.values, cmap="RdBu_r", vmin=-1, vmax=1)

    labels = [d.replace("_", " ") for d in drivers]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8.5)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.grid(visible=False)

    for i in range(len(labels)):
        for j in range(len(labels)):
            value = matrix.values[i, j]
            # Witte tekst op donkere cellen, zwarte op lichte.
            colour = "white" if abs(value) > 0.55 else ROLE["ink"]
            weight = "bold" if i != j and abs(value) > 0.5 else "normal"
            ax.text(
                j,
                i,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color=colour,
                fontweight=weight,
            )

    colourbar = fig.colorbar(image, ax=ax, shrink=0.72)
    colourbar.set_label("Correlatie", fontsize=9)

    ax.set_title(
        "Correlaties tussen de drivers onderling\n"
        "(vetgedrukt: boven 0,5 — hier ontstaat multicollineariteit)",
        fontsize=11,
    )

    fig.tight_layout()
    path = save_figure(fig, filename)

    # Zoek de probleempaar-combinaties.
    problem_pairs = []
    for i, first in enumerate(drivers):
        for j, second in enumerate(drivers):
            if j <= i:
                continue
            value = float(matrix.values[i, j])
            if abs(value) > 0.5:
                problem_pairs.append(
                    {"driver_a": first, "driver_b": second, "correlatie": value}
                )
    return path, pd.DataFrame(problem_pairs)
