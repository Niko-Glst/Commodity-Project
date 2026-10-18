"""Maakt de zes paperfiguren uit de bevroren resultaten.

Waarom een apart script
-----------------------
De figuren horen bij de bevroren getallen, maar je wilt ze kunnen opmaken
zonder de hele analyse opnieuw te draaien. Daarom twee ingangen:

    build_all(...)   wordt aangeroepen door freeze_results.py, met de
                     objecten die daar al in het geheugen staan;
    main()           leest results/ en de datacache, en controleert eerst dat
                     elk getal dat op een figuur komt de bevroren waarde
                     reproduceert. Zo niet, dan stopt het zonder te schrijven.

Opmaak
------
Engelse labels en een titel boven elke figuur, Arial, 6,5 inch breed,
vector-PDF met ingebedde TrueType-fonts (fonttype 42) en PNG op 300 dpi. Elke reeks heeft in alle figuren dezelfde kleur, en lijnen
verschillen ook in stijl zodat de figuren in zwart-wit leesbaar blijven.

Gebruik:
    python scripts/make_figures.py
"""

from __future__ import annotations

import json
import sys
import warnings
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.viz.style import ROLE  # noqa: E402

RESULTS = PROJECT_ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"

FIGURE_NAMES = (
    "fig1_return_distribution",
    "fig2_volatility_clustering",
    "fig3_oos_r2",
    "fig4_buffer_vs_rule_of_thumb",
    "fig5_gold_not_an_equity_hedge",
    "fig6_buffer_depends_on_start_state",
)

FIGSIZE = (6.5, 4.0)
# Figuur 2 heeft twee panelen onder elkaar en krijgt daarom meer hoogte.
FIGSIZES = {name: FIGSIZE for name in FIGURE_NAMES}
FIGSIZES["fig2_volatility_clustering"] = (6.5, 5.6)

FONT_SIZE = 10  # in de paper (0,82 x tekstbreedte) ongeveer 8,2 pt
NOTE_SIZE = 9
TITLE_SIZE = 11

# Eén kleur per reeks, in alle figuren dezelfde, en dezelfde rollen als de
# rest van het project (goldmodel.viz.style): waargenomen data blauw,
# modeluitkomsten oranje.
COLOURS = {
    "gold": ROLE["empirical"],       # waargenomen goud
    "reference": ROLE["reference"],  # normale verdeling, steekproefgemiddelde, naïeve benchmarks
    "regression": ROLE["secondary"],  # OLS en ridge
    "garch": ROLE["theoretical"],    # GARCH-t-uitkomsten
    "rule": ROLE["ink_soft"],        # vuistregels
    "ink": ROLE["ink"],              # nullijnen
}

STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT_SIZE,
    "axes.labelsize": FONT_SIZE,
    "xtick.labelsize": FONT_SIZE,
    "ytick.labelsize": FONT_SIZE,
    "legend.fontsize": NOTE_SIZE,
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#E6E6E6",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "axes.unicode_minus": True,
    "axes.titlesize": FONT_SIZE,
    "axes.titlelocation": "left",
    "figure.titlesize": TITLE_SIZE,
    "figure.titleweight": "bold",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.dpi": 300,
}


def signed(value: float, decimals: int = 4) -> str:
    """Formatteert met een echt minteken en een plus voor positieve waarden."""
    if round(value, decimals) == 0:
        return f"{0:.{decimals}f}"
    return f"{value:+.{decimals}f}".replace("-", "−")


def new_figure(stem: str, title: str, **kwargs) -> tuple[plt.Figure, object]:
    """Maakt een figuur op het afgesproken formaat, met titel."""
    fig, axes = plt.subplots(figsize=FIGSIZES[stem], layout="constrained", **kwargs)
    fig.suptitle(title)
    return fig, axes


def save(fig: plt.Figure, stem: str) -> None:
    """Schrijft PDF en PNG op exact het opgegeven formaat (geen tight bbox).

    De PDF krijgt geen aanmaakdatum mee. Anders verschilt elk bestand bij
    elke run, ook als er niets veranderd is, en ziet git elke freeze als
    een wijziging van alle figuren.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", metadata={"CreationDate": None})
    fig.savefig(FIGURES / f"{stem}.png", dpi=300)
    plt.close(fig)
    print(f"    {stem}.pdf + .png")


# -- de zes figuren -------------------------------------------------------


def figure_return_distribution(gold: pd.Series, numbers: dict) -> None:
    """F1: verdeling van dagrendementen, lineair en logaritmisch."""
    returns = gold.to_numpy() * 100
    mean, std = returns.mean(), returns.std(ddof=1)

    fig, (left, right) = new_figure(
        "fig1_return_distribution",
        "Daily gold returns versus the normal distribution",
        ncols=2, gridspec_kw={"width_ratios": [1.15, 1]},
    )
    left.set_title("(a) Linear scale")
    right.set_title("(b) Log scale: the tails")
    # Bakken over de hele reeks, zodat de dichtheid over alle waarnemingen
    # genormeerd is; links tonen we alleen het midden.
    edges = np.arange(np.floor(returns.min()), np.ceil(returns.max()) + 0.125, 0.125)
    left.hist(returns, bins=edges, density=True, color=COLOURS["gold"], alpha=0.75,
              label=f"Gold futures\n(n = {numbers['n_trading_days']:,})")
    grid = np.linspace(-6, 6, 600)
    left.plot(grid, sps.norm.pdf(grid, mean, std), ls="--", lw=1.4,
              color=COLOURS["reference"], label="Normal, same\nmean and std")
    left.set_xlim(-6, 6)
    left.set_xlabel("Daily log return (%)")
    left.set_ylabel("Density")
    left.legend(loc="upper left", handlelength=1.8)

    wide = np.arange(np.floor(returns.min()), np.ceil(returns.max()) + 0.5, 0.5)
    right.hist(returns, bins=wide, density=True, histtype="stepfilled",
               color=COLOURS["gold"], alpha=0.75)
    span = np.linspace(wide[0], wide[-1], 600)
    right.plot(span, sps.norm.pdf(span, mean, std), ls="--", lw=1.4,
               color=COLOURS["reference"])
    # Zelfde definitie als key_numbers: |r| > 3 sigma, rond nul.
    for side in (-1, 1):
        right.axvline(side * 3 * std, ymax=0.78, ls=":", lw=0.9, color=COLOURS["ink"])
    right.set_yscale("log")
    right.set_ylim(1e-4, 10)
    right.set_xlabel("Daily log return (%)")
    right.set_ylabel("Density (log scale)")
    right.text(
        0.03, 0.97,
        f"Excess kurtosis {numbers['kurtosis_excess']:.2f}\n"
        f"Beyond ±3σ: {numbers['days_beyond_3sigma']} days\n"
        f"Normal expects {numbers['days_beyond_3sigma_normal_expectation']} days",
        transform=right.transAxes, va="top", ha="left", fontsize=NOTE_SIZE,
    )
    save(fig, "fig1_return_distribution")


def figure_volatility_clustering(gold: pd.Series, numbers: dict) -> None:
    """F2: volatiliteitsclustering, in de tijd en als autocorrelatie.

    Paneel (a) laat zien dat onrust in blokken komt. Paneel (b) is dezelfde
    autocorrelatie als in de verkenningsfiguur 05 (40 lags, band 1,96/sqrt(n)):
    de richting van morgen hangt niet aan vandaag, de grootte wel. Dat is de
    brug tussen het voorspeldeel en het bufferdeel van de paper.
    """
    from statsmodels.tsa.stattools import acf

    rolling = (gold.rolling(63).std() * np.sqrt(252) * 100).dropna()
    full_sample = numbers["annualised_volatility"] * 100

    fig, (top, bottom) = new_figure(
        "fig2_volatility_clustering",
        "Volatility clustering: the size of moves persists, the direction does not",
        nrows=2, gridspec_kw={"height_ratios": [1, 1]},
    )
    top.set_title("(a) 63-day rolling volatility")
    top.plot(rolling.index, rolling.to_numpy(), lw=0.9, color=COLOURS["gold"],
             label="63-day rolling volatility")
    top.axhline(full_sample, ls="--", lw=1.2, color=COLOURS["reference"],
                label=f"Full-sample volatility ({full_sample:.2f}% p.a.)")
    top.set_xlim(rolling.index[0], rolling.index[-1])
    top.set_ylim(0, 50)
    top.set_xlabel("Year")
    top.set_ylabel("Volatility (% p.a.)")
    top.legend(loc="upper center", handlelength=2.2, ncols=2)

    n_lags = 40
    lags = np.arange(1, n_lags + 1)
    returns_acf = acf(gold.to_numpy(), nlags=n_lags, fft=True)[1:]
    absolute_acf = acf(np.abs(gold.to_numpy()), nlags=n_lags, fft=True)[1:]
    band = 1.96 / np.sqrt(len(gold))
    width = 0.4

    bottom.set_title("(b) Autocorrelation of daily returns and of their size")
    bottom.bar(lags - width / 2, returns_acf, width=width, color=COLOURS["reference"],
               label="Returns (direction)")
    bottom.bar(lags + width / 2, absolute_acf, width=width, color=COLOURS["gold"],
               label="Absolute returns (size)")
    for side in (-1, 1):
        bottom.axhline(side * band, ls="--", lw=0.9, color=COLOURS["rule"])
    bottom.axhline(0, color=COLOURS["ink"], lw=0.8)
    bottom.plot([], [], ls="--", lw=0.9, color=COLOURS["rule"],
                label="95% band under no autocorrelation")
    bottom.set_xlim(0, n_lags + 1)
    bottom.set_ylim(-0.05, 0.2)
    bottom.set_xlabel("Lag (trading days)")
    bottom.set_ylabel("Autocorrelation")
    bottom.legend(loc="upper right", ncols=1)
    save(fig, "fig2_volatility_clustering")


def figure_oos_r2(metrics: pd.DataFrame) -> None:
    """F3: out-of-sample R-kwadraat per model."""
    order = [
        ("random_walk", "Random walk\n(zero forecast)", "reference"),
        ("historisch", "Historical\nmean", "reference"),
        ("ols", "OLS", "regression"),
        ("ridge", "Ridge", "regression"),
    ]
    values = [float(metrics.loc[key, "r2_oos"]) for key, _, _ in order]

    fig, ax = new_figure(
        "fig3_oos_r2",
        "Out-of-sample R²: macro drivers add almost nothing to a zero forecast",
    )
    for position, ((_, label, colour), value) in enumerate(zip(order, values)):
        benchmark = colour == "reference"
        ax.bar(position, value, width=0.6, color=COLOURS[colour],
               hatch="///" if benchmark else None,
               edgecolor="white" if benchmark else COLOURS[colour], linewidth=0)
        offset = 0.0004 if value >= 0 else -0.0004
        ax.text(position, value + offset, signed(value), ha="center",
                va="bottom" if value >= 0 else "top", fontsize=NOTE_SIZE)
    ax.axhline(0, color=COLOURS["ink"], lw=0.8)
    ax.set_xticks(range(len(order)), [label for _, label, _ in order])
    ax.set_ylim(-0.003, 0.0135)
    ax.set_ylabel("Out-of-sample $R^2$ (vs zero forecast)")
    save(fig, "fig3_oos_r2")


def figure_buffer_vs_rule(max_adverse: np.ndarray, numbers: dict) -> None:
    """F4: empirische CDF van de maximale tegenbeweging per kwartaal."""
    excursions = np.sort(max_adverse) * 100
    covered = np.arange(1, len(excursions) + 1) / len(excursions) * 100
    buffer_99 = numbers["buffer_99_garch_t"] * 100

    fig, ax = new_figure(
        "fig4_buffer_vs_rule_of_thumb",
        "Rules of thumb cover far fewer quarters than a 99% buffer",
    )
    ax.plot(excursions, covered, lw=1.6, color=COLOURS["garch"],
            label=f"GARCH-t, {len(excursions):,} simulated quarters")
    ax.axhline(99, ls=":", lw=0.9, color=COLOURS["reference"])
    ax.text(69, 97.5, "99% of paths", ha="right", va="top", fontsize=NOTE_SIZE,
            color=COLOURS["reference"])

    # De dekking als punt op de curve, met het label in het lege vlak eronder;
    # naast de lijnen kruist de 5%-tekst anders de 10%-lijn.
    for rule, style, height in ((5, "--", 22), (10, "-.", 48)):
        coverage = numbers[f"coverage_of_{rule}pct_rule"] * 100
        ax.axvline(rule, ls=style, lw=1.2, color=COLOURS["rule"])
        ax.plot(rule, coverage, "o", ms=4.5, color=COLOURS["rule"], zorder=4)
        ax.annotate(
            f"{rule}% rule covers {coverage:.2f}%", (rule, coverage),
            xytext=(14, height), textcoords="data", va="center",
            fontsize=NOTE_SIZE, color=COLOURS["rule"],
            arrowprops={"arrowstyle": "-", "lw": 0.7, "color": COLOURS["rule"],
                        "shrinkA": 2, "shrinkB": 3},
        )
    ax.axvline(buffer_99, ls="-", lw=1.2, color=COLOURS["garch"])
    ax.text(buffer_99 + 0.8, 50, f"99% buffer\n{buffer_99:.2f}% of notional",
            fontsize=NOTE_SIZE, va="center", color=COLOURS["garch"])

    ax.set_xlim(0, 70)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Maximum adverse move over one quarter (% of notional)")
    ax.set_ylabel("Simulated quarters covered (%)")
    ax.legend(loc="lower right")
    save(fig, "fig4_buffer_vs_rule_of_thumb")


def figure_equity_hedge(hedge: dict) -> None:
    """F5: correlatie goud / S&P 500, volledig en in stressperiodes."""
    bars = [
        ("Full sample\n2003 to 2026", hedge["corr_gold_sp500"]),
        ("2008\nGFC", hedge["corr_gold_sp500_stress_2008"]),
        ("March\n2020", hedge["corr_gold_sp500_stress_maart"]),
        ("2022\nbear market", hedge["corr_gold_sp500_stress_2022"]),
    ]
    low, high = hedge["corr_gold_sp500_ci_low"], hedge["corr_gold_sp500_ci_high"]
    full = bars[0][1]

    fig, ax = new_figure(
        "fig5_gold_not_an_equity_hedge",
        "Gold does not hedge equities, not even in stress periods",
    )
    ax.bar(range(len(bars)), [value for _, value in bars], width=0.6,
           color=COLOURS["gold"])
    ax.errorbar(0, full, yerr=[[full - low], [high - full]], fmt="none",
                ecolor=COLOURS["ink"], elinewidth=1, capsize=4)
    # Naast de foutbalk: gecentreerd erboven loopt de tekst over de y-as.
    ax.text(0.34, full, signed(full), ha="left", va="center", fontsize=NOTE_SIZE)
    ax.text(0.08, high, f"95% CI [{signed(low)}, {signed(high)}]",
            ha="left", va="center", fontsize=NOTE_SIZE)
    for position, (_, value) in enumerate(bars[1:], start=1):
        offset = 0.004 if value >= 0 else -0.004
        ax.text(position, value + offset, signed(value), ha="center",
                va="bottom" if value >= 0 else "top", fontsize=NOTE_SIZE)
    ax.axhline(0, color=COLOURS["ink"], lw=0.8)
    ax.set_xticks(range(len(bars)), [label for label, _ in bars])
    ax.set_ylim(-0.06, 0.10)
    ax.set_ylabel("Correlation of daily returns,\ngold vs S&P 500")
    save(fig, "fig5_gold_not_an_equity_hedge")


def figure_start_state(conditional: pd.DataFrame, drift_rows: list[dict] | None,
                       frozen_end_date: str) -> None:
    """F6: de 99%-buffer als functie van de startvolatiliteit.

    De gecontroleerde sweep is het bewijs van het mechanisme; de zes
    einddatums laten zien hoe het in de praktijk opdook.
    """
    fig, ax = new_figure(
        "fig6_buffer_depends_on_start_state",
        "The 99% buffer depends on volatility at the start date",
    )
    ax.plot(conditional["start_vol_pct"], conditional["buffer_99_pct"],
            ls="-", marker="o", ms=5, lw=1.4, color=COLOURS["garch"], zorder=3,
            label="Controlled sweep: fixed sample, start volatility varied")

    if drift_rows:
        frame = pd.DataFrame(drift_rows)
        ax.scatter(frame["startvol_pct"], frame["buffer_99_pct"], s=42, marker="s",
                   facecolor="white", edgecolor=COLOURS["gold"], linewidth=1.4,
                   zorder=4, label="Re-estimated at six end dates")
        # Labels links of rechts, zodat ze niet over elkaar of over de lijn vallen.
        placement = {
            "2025-09-30": (8, -10, "left"),
            "2025-12-31": (8, -10, "left"),
            "2026-03-31": (8, -4, "left"),
            "2026-06-30": (8, -10, "left"),
            "2026-09-30": (-8, 4, "right"),
            "2026-10-13": (-8, 2, "right"),
        }
        for _, row in frame.iterrows():
            dx, dy, align = placement.get(row["einddatum"], (8, -4, "left"))
            label = row["einddatum"]
            if label == frozen_end_date:
                label += " (frozen)"
            ax.annotate(label, (row["startvol_pct"], row["buffer_99_pct"]),
                        textcoords="offset points", xytext=(dx, dy), ha=align,
                        fontsize=NOTE_SIZE, color=COLOURS["gold"])

    ax.set_xlim(10, 45)
    ax.set_ylim(15, 80)
    ax.set_xlabel("Annualised volatility at start (% p.a.)")
    ax.set_ylabel("99% buffer (% of notional)")
    ax.legend(loc="upper left")
    save(fig, "fig6_buffer_depends_on_start_state")


def build_all(
    *,
    gold: pd.Series,
    max_adverse: np.ndarray,
    numbers: dict,
    metrics: pd.DataFrame,
    conditional: pd.DataFrame,
    hedge: dict | None,
    drift_rows: list[dict] | None,
    frozen_end_date: str,
) -> None:
    """Maakt alle zes figuren.

    Argumenten:
        numbers: Naam -> waarde (dus zonder de metadatavelden van
            key_numbers.json); zie ``plain_numbers``.
    """
    with plt.rc_context(STYLE):
        figure_return_distribution(gold, numbers)
        figure_volatility_clustering(gold, numbers)
        figure_oos_r2(metrics)
        figure_buffer_vs_rule(max_adverse, numbers)
        if hedge is not None:
            figure_equity_hedge(hedge)
        figure_start_state(conditional, drift_rows, frozen_end_date)


def plain_numbers(records: dict) -> dict:
    """Haalt de waarden uit {naam: {"value": ..., "unit": ...}}."""
    return {name: entry["value"] for name, entry in records.items()}


# -- losse run vanaf de bevroren uitvoer ----------------------------------


def _check(name: str, recomputed: float, frozen: float, decimals: int) -> None:
    """Stopt als een herberekend getal niet de bevroren waarde geeft."""
    if round(recomputed, decimals) != round(frozen, decimals):
        raise SystemExit(
            f"{name}: herberekend {recomputed:.6f}, bevroren {frozen}. "
            "De data of de code is veranderd sinds het bevriezen; er is niets "
            "geschreven."
        )
    print(f"    ok  {name} = {frozen}")


def main() -> int:
    """Leest results/ en de cache, controleert, en schrijft de figuren."""
    warnings.simplefilter("ignore")
    from goldmodel.config import ALL_SERIES, ANALYSIS_END_DATE, DEFAULT_FETCH_SETTINGS
    from goldmodel.data.loader import DataLoader
    from goldmodel.simulate import SimulationSettings, fit_garch, simulate_garch
    from goldmodel.viz.correlations import build_change_panel

    frozen = json.loads((RESULTS / "key_numbers.json").read_text(encoding="utf-8"))
    numbers = plain_numbers(frozen["numbers"])
    manifest = frozen["_manifest"]

    # Alleen de cache: een oneindige TTL voorkomt dat de loader gaat ophalen.
    settings = replace(DEFAULT_FETCH_SETTINGS, cache_ttl_hours=float("inf"))
    report = DataLoader(settings).load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    gold = build_change_panel(panel)["gold_futures"].dropna()

    print("Controle tegen key_numbers.json")
    _check("n_trading_days", len(gold), numbers["n_trading_days"], 0)
    _check("annualised_volatility", gold.std() * np.sqrt(252),
           numbers["annualised_volatility"], 4)
    _check("kurtosis_excess", sps.kurtosis(gold, fisher=True),
           numbers["kurtosis_excess"], 3)
    _check("days_beyond_3sigma",
           int((gold.abs() > 3 * gold.std()).sum()),
           numbers["days_beyond_3sigma"], 0)

    # F4 heeft de losse paden nodig; die zijn niet bevroren, dus opnieuw
    # simuleren met dezelfde seed en controleren op de bevroren uitkomsten.
    garch = fit_garch(gold)
    simulation = simulate_garch(
        float(gold.mean()), garch,
        SimulationSettings(n_paths=manifest["n_paths"], horizon_days=63,
                           seed=manifest["seed"], is_short=True),
    )
    _check("buffer_99_garch_t", simulation.value_at_risk(0.99),
           numbers["buffer_99_garch_t"], 4)
    for rule in (5, 10):
        _check(f"coverage_of_{rule}pct_rule",
               float((simulation.max_adverse <= rule / 100).mean()),
               numbers[f"coverage_of_{rule}pct_rule"], 4)

    metrics = pd.read_csv(TABLES / "walk_forward_metrics.csv", index_col="model")
    conditional = pd.read_csv(TABLES / "buffer_conditional_on_start_state.csv")
    hedge_path = RESULTS / "hedge_numbers.json"
    drift_path = RESULTS / "drift_numbers.json"
    hedge = json.loads(hedge_path.read_text(encoding="utf-8")) if hedge_path.exists() else None
    drift = json.loads(drift_path.read_text(encoding="utf-8")) if drift_path.exists() else None

    print("Figuren")
    build_all(
        gold=gold,
        max_adverse=simulation.max_adverse,
        numbers=numbers,
        metrics=metrics,
        conditional=conditional,
        hedge=hedge,
        drift_rows=drift["rows"] if drift else None,
        frozen_end_date=ANALYSIS_END_DATE,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
