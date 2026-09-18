"""Uitlegfiguren voor de overgang van fase 1 naar fase 2.

Fase 1 keek naar één reeks: hoe beweegt goud? Fase 2 kijkt naar twee reeksen
tegelijk: beweegt goud mee met de rente? Dat is een andere vraag, en er komt
een probleem bij kijken dat bij één reeks niet bestaat.

Deze module legt dat probleem uit met zo weinig statistiek als mogelijk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from goldmodel.viz.style import ROLE, annotate, save_figure


def plot_why_two_series_is_different(filename: str = "15_van_een_naar_twee.png"):
    """Legt uit waarom twee reeksen vergelijken een nieuw probleem geeft.

    Vier panelen, van een alledaags voorbeeld naar de kern van het probleem.
    Geen enkele statistische toets; alleen kijken.
    """
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))
    ax_absurd, ax_scatter = axes[0]
    ax_trend, ax_detrended = axes[1]

    # -- 1. Een absurd voorbeeld ----------------------------------------
    years = np.arange(2003, 2027)
    population = 16.2 + (years - 2003) * 0.08
    subscribers = 1.5 + (years - 2003) * 12.0

    # Twee y-assen. Dat is normaal gesproken een slechte keuze: je kunt de
    # hoogtes niet vergelijken en met de schalen valt elke gewenste
    # "samenhang" te fabriceren. Hier is dat juist het punt van de figuur -
    # dat twee reeksen samen omhoog lopen zegt niets - en de eenheden
    # (inwoners tegenover abonnees) zijn onvergelijkbaar. Op één as wordt de
    # vlakkere reeks plat gedrukt en verdwijnt de gelijkenis die we willen
    # laten zien. Nergens anders in dit project een dubbele as gebruiken.
    ax_absurd.plot(
        years,
        population,
        color=ROLE["empirical"],
        linewidth=2.6,
        marker="o",
        markersize=4,
        label="Nederlandse bevolking (links)",
    )
    ax_absurd.set_ylabel("Bevolking (miljoen)", color=ROLE["empirical"])
    ax_absurd.tick_params(axis="y", labelcolor=ROLE["empirical"])

    ax_subs = ax_absurd.twinx()
    ax_subs.plot(
        years,
        subscribers,
        color=ROLE["theoretical"],
        linewidth=2.6,
        marker="s",
        markersize=4,
        label="Netflix-abonnees (rechts)",
    )
    ax_subs.set_ylabel("Netflix-abonnees (miljoen)", color=ROLE["theoretical"])
    ax_subs.tick_params(axis="y", labelcolor=ROLE["theoretical"])
    ax_subs.grid(visible=False)

    ax_absurd.set_title("1. Twee dingen die allebei groeien", fontsize=11)
    handles = [
        plt.Line2D([], [], color=ROLE["empirical"], marker="o", label="NL bevolking"),
        plt.Line2D([], [], color=ROLE["theoretical"], marker="s", label="Netflix"),
    ]
    ax_absurd.legend(handles=handles, loc="upper left", fontsize=8.5)
    annotate(
        ax_absurd,
        "Beide lopen omhoog.\n\n"
        "Ze hebben niets met elkaar\n"
        "te maken, maar hun\n"
        "correlatie is +1,00.",
        loc="lower right",
    )

    # -- 2. Waarom de correlatie hoog is --------------------------------
    ax_scatter.scatter(
        population, subscribers, s=55, color=ROLE["empirical"], zorder=5
    )
    ax_scatter.plot(
        population, subscribers, color=ROLE["highlight"], linewidth=1.6, alpha=0.7
    )
    ax_scatter.set_xlabel("Nederlandse bevolking (miljoen)")
    ax_scatter.set_ylabel("Netflix-abonnees (miljoen)")
    ax_scatter.set_title("2. Uitgezet tegen elkaar: een rechte lijn", fontsize=11)
    annotate(
        ax_scatter,
        "Een regressie vindt hier een\n"
        "perfect verband.\n\n"
        "Maar het enige wat de twee\n"
        "delen is DE TIJD. Beide gaan\n"
        "omhoog, dus bewegen ze samen.",
        loc="upper left",
    )

    # -- 3. Hetzelfde met de goudprijs ----------------------------------
    rng = np.random.default_rng(3)
    n = 250
    time = np.arange(n)
    gold_like = 100 + time * 0.8 + np.cumsum(rng.standard_normal(n)) * 2
    unrelated = 50 + time * 0.5 + np.cumsum(rng.standard_normal(n)) * 2

    ax_trend.plot(
        time, gold_like, color=ROLE["empirical"], linewidth=1.6, label="reeks A"
    )
    ax_trend.plot(
        time, unrelated, color=ROLE["theoretical"], linewidth=1.6, label="reeks B"
    )
    ax_trend.set_xlabel("Tijd")
    ax_trend.set_ylabel("Niveau")
    ax_trend.set_title("3. Nu met toevalsruis erbij", fontsize=11)
    ax_trend.legend(loc="upper left", fontsize=8.5)

    correlation_levels = float(pd.Series(gold_like).corr(pd.Series(unrelated)))
    annotate(
        ax_trend,
        f"Correlatie: {correlation_levels:+.2f}\n\n"
        "Ook hier: allebei omhoog,\n"
        "dus hoge correlatie. En ook\n"
        "hier is er geen verband.",
        loc="lower right",
    )

    # -- 4. De oplossing: kijk naar de veranderingen --------------------
    changes_a = np.diff(gold_like)
    changes_b = np.diff(unrelated)

    ax_detrended.scatter(
        changes_b, changes_a, s=14, color=ROLE["secondary"], alpha=0.6
    )
    ax_detrended.axhline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_detrended.axvline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_detrended.set_xlabel("Dagverandering reeks B")
    ax_detrended.set_ylabel("Dagverandering reeks A")
    ax_detrended.set_title("4. Kijk naar de VERANDERINGEN per dag", fontsize=11)

    correlation_changes = float(
        pd.Series(changes_a).corr(pd.Series(changes_b))
    )
    annotate(
        ax_detrended,
        f"Correlatie: {correlation_changes:+.2f}\n\n"
        "Een wolk zonder richting.\n"
        "Dit is de waarheid: er is\n"
        "geen verband.\n\n"
        "De trend zat in de weg.",
        loc="upper left",
    )

    fig.suptitle(
        "Van één reeks naar twee: waarom 'samen omhoog' geen verband is",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


def plot_what_the_tests_do(
    panel: pd.DataFrame, filename: str = "16_wat_toetsen_doen.png"
):
    """Laat zien wat ADF en KPSS eigenlijk meten, met echte goudprijzen.

    De toetsen beantwoorden één vraag: heeft deze reeks een vast niveau waar
    hij naar terugkeert, of loopt hij weg? Die vraag is visueel te stellen,
    en dat doen we hier eerst — de toets is daarna alleen een formele
    bevestiging.
    """
    prices = panel["gold_futures"].dropna()
    returns = np.log(prices / prices.shift(1)).dropna() * 100

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.5))
    ax_price, ax_price_hist = axes[0]
    ax_ret, ax_ret_hist = axes[1]

    # -- boven: de prijs, die wegloopt ----------------------------------
    ax_price.plot(prices.index, prices.values, color=ROLE["empirical"], linewidth=1.1)

    # Markeer het gemiddelde van de eerste en de laatste vijf jaar.
    early = prices.loc[:"2008"]
    late = prices.loc["2021":]
    ax_price.axhline(
        early.mean(),
        color=ROLE["highlight"],
        linestyle="--",
        linewidth=1.8,
        label=f"gem. 2003-2008: ${early.mean():,.0f}",
    )
    ax_price.axhline(
        late.mean(),
        color=ROLE["theoretical"],
        linestyle="--",
        linewidth=1.8,
        label=f"gem. 2021-2026: ${late.mean():,.0f}",
    )
    ax_price.set_ylabel("Goudprijs (USD)")
    ax_price.set_title("De PRIJS: waar is het gemiddelde?", fontsize=11)
    ax_price.legend(loc="upper left", fontsize=8.5)
    annotate(
        ax_price,
        "Er is geen antwoord op\n"
        "'wat is de normale goudprijs'.\n\n"
        "Het hangt af van de periode.\n"
        "Zo'n reeks heet NIET-\n"
        "STATIONAIR.",
        loc="lower right",
    )

    # Histogram van de prijs: geen enkele piek, breed uitgesmeerd.
    ax_price_hist.hist(
        prices.values, bins=60, color=ROLE["empirical"], alpha=0.75
    )
    ax_price_hist.set_xlabel("Goudprijs (USD)")
    ax_price_hist.set_ylabel("Aantal dagen")
    ax_price_hist.set_title("Geen duidelijk 'normaal' niveau", fontsize=11)
    annotate(
        ax_price_hist,
        "Breed uitgesmeerd, meerdere\n"
        "bulten. Er is geen waarde\n"
        "waar de prijs steeds\n"
        "naar terugkeert.",
        loc="upper right",
    )

    # -- onder: de rendementen, die terugkeren --------------------------
    ax_ret.plot(
        returns.index, returns.values, color=ROLE["secondary"], linewidth=0.5, alpha=0.8
    )
    early_returns = returns.loc[:"2008"]
    late_returns = returns.loc["2021":]
    ax_ret.axhline(
        early_returns.mean(),
        color=ROLE["highlight"],
        linestyle="--",
        linewidth=1.8,
        label=f"gem. 2003-2008: {early_returns.mean():+.3f}%",
    )
    ax_ret.axhline(
        late_returns.mean(),
        color=ROLE["theoretical"],
        linestyle="--",
        linewidth=1.8,
        label=f"gem. 2021-2026: {late_returns.mean():+.3f}%",
    )
    ax_ret.set_ylabel("Dagrendement (%)")
    ax_ret.set_title("De RENDEMENTEN: wel een vast gemiddelde", fontsize=11)
    ax_ret.legend(loc="upper left", fontsize=8.5)
    annotate(
        ax_ret,
        "De twee gemiddelden liggen\n"
        "vlak bij elkaar, vlak bij nul.\n\n"
        "Zo'n reeks heet STATIONAIR.",
        loc="lower right",
    )

    ax_ret_hist.hist(returns.values, bins=80, color=ROLE["secondary"], alpha=0.75)
    ax_ret_hist.axvline(0, color=ROLE["ink_soft"], linewidth=1.2)
    ax_ret_hist.set_xlabel("Dagrendement (%)")
    ax_ret_hist.set_ylabel("Aantal dagen")
    ax_ret_hist.set_title("Eén duidelijke piek rond nul", fontsize=11)
    annotate(
        ax_ret_hist,
        "Eén piek, rond nul.\n"
        "De rendementen keren steeds\n"
        "hiernaar terug.\n\n"
        "(Dit is de figuur uit fase 1,\n"
        "met de dikke staarten.)",
        loc="upper right",
    )

    fig.suptitle(
        "Wat ADF en KPSS meten: heeft de reeks een vast niveau?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)
