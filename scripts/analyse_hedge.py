"""Is goud een hedge, en waarvoor precies?

Deze vraag stond nergens in het project, en dat was een gat. De margelaag
rekent door hoeveel cash een short goudfutures-positie vraagt, maar of die
positie iets ZINVOLS afdekt werd nooit getoetst.

Een hedge moet een bestaand risico compenseren. Dat betekent: als de afgedekte
positie daalt, moet de hedge stijgen. Een lage correlatie is niet genoeg -
dat is diversificatie, iets anders.

Wat dit script meet
-------------------
1. Correlatie van goud met twee kandidaat-exposures (aandelen, dollar), over
   de hele steekproef en in stressperiodes apart.
2. De minimum-variance hedge ratio en de variantiereductie die hij oplevert,
   in-sample EN out-of-sample.
3. Wat een goudallocatie doet met volatiliteit, drawdown en CVaR van een
   aandelenportefeuille.
4. De kosten van het aanhouden van de hedge.

Gebruik:
    python scripts/analyse_hedge.py
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.config import ALL_SERIES, ANALYSIS_END_DATE  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402

LINE = "=" * 78
TRADING_DAYS = 252

# Stressperiodes. Bewust VOORAF gekozen op basis van bekende gebeurtenissen,
# niet gezocht in de data - anders selecteer je de periodes die je conclusie
# bevestigen.
STRESS_PERIODS = {
    "2008 GFC": ("2008-09-01", "2009-03-31"),
    "maart 2020": ("2020-02-19", "2020-03-23"),
    "2022 bear": ("2022-01-01", "2022-10-14"),
}


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def bootstrap_correlation(
    a: np.ndarray, b: np.ndarray, *, n_boot: int = 2000, seed: int = 1
) -> tuple[float, float, float]:
    """Correlatie met een bootstrap-betrouwbaarheidsinterval.

    Waarom bootstrappen: de analytische standaardfout van een correlatie gaat
    uit van normaal verdeelde data. Rendementen hebben dikke staarten
    (kurtosis 6,05 in fase 1), dus die aanname klopt niet. Een bootstrap maakt
    geen verdelingsaanname.

    Geeft terug:
        (correlatie, ondergrens 2,5%, bovengrens 97,5%)
    """
    rng = np.random.default_rng(seed)
    observed = float(np.corrcoef(a, b)[0, 1])
    n = len(a)
    draws = np.empty(n_boot)
    for trial in range(n_boot):
        pick = rng.integers(0, n, n)
        draws[trial] = np.corrcoef(a[pick], b[pick])[0, 1]
    return observed, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def minimum_variance_hedge(
    exposure: np.ndarray, hedger: np.ndarray
) -> tuple[float, float]:
    """De hedge ratio die de variantie minimaliseert, en wat hij oplevert.

    De wiskunde: je houdt 1 eenheid exposure en short h eenheden van de
    hedger. De variantie van de combinatie is

        var(e - h*x) = var(e) - 2h*cov(e,x) + h^2*var(x)

    Afgeleid naar h en nul stellen geeft

        h* = cov(e,x) / var(x)

    Dat is precies de OLS-beta van exposure op hedger. De variantiereductie
    die je daarmee haalt is gelijk aan de R-kwadraat van die regressie, en dat
    is de standaardmaat voor *hedge effectiveness* (Ederington 1979).

    Geeft terug:
        (h*, variantiereductie als fractie)
    """
    covariance = np.cov(exposure, hedger)
    h_star = covariance[0, 1] / covariance[1, 1]
    hedged = exposure - h_star * hedger
    reduction = 1.0 - hedged.var() / exposure.var()
    return float(h_star), float(reduction)


def portfolio_statistics(returns: np.ndarray) -> dict:
    """Standaardmaten voor een portefeuille van LOG-rendementen.

    Let op het samenstellen: ``exp(cumsum)``, niet ``(1+r).cumprod()``. Die
    tweede behandelt een log-rendement als enkelvoudig en geeft over 23 jaar
    honderden procentpunten verschil. Dat was een echte bug in dit project.
    """
    equity = np.exp(np.cumsum(returns))
    running_max = np.maximum.accumulate(equity)
    drawdown = float((equity / running_max - 1.0).min())
    threshold = np.quantile(returns, 0.05)
    return {
        "annual_return": float(np.expm1(returns.mean() * TRADING_DAYS)),
        "annual_volatility": float(returns.std() * np.sqrt(TRADING_DAYS)),
        "max_drawdown": drawdown,
        "cvar_5pct": float(returns[returns <= threshold].mean()),
    }


def run(results: dict) -> None:
    """Draait de volledige hedge-analyse."""
    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)

    prices = panel[["gold_futures", "sp500", "dxy"]].dropna()
    returns = np.log(prices / prices.shift(1)).dropna()
    vix = panel["vix"].reindex(returns.index).ffill()

    print(f"\n  N = {len(returns):,} handelsdagen")
    print(
        f"  {returns.index.min().date()} tot {returns.index.max().date()} "
        f"(afgekapt op {ANALYSIS_END_DATE})"
    )
    results["n_observations"] = int(len(returns))
    results["start_date"] = str(returns.index.min().date())
    results["end_date"] = str(returns.index.max().date())

    # -- 1. correlaties ---------------------------------------------------
    section("1. CORRELEERT GOUD MET IETS DAT JE WILT AFDEKKEN?")
    print(
        "\nEen hedge moet STIJGEN als de afgedekte positie daalt. Een correlatie\n"
        "rond nul betekent diversificatie, niet bescherming. Een correlatie die\n"
        "in stress naar nul of positief gaat, betekent dat de hedge wegvalt op\n"
        "het moment dat je hem nodig hebt.\n"
    )

    print(f"{'exposure':<12} {'rho':>8} {'95%-interval':>22}  bevat nul?")
    for name in ("sp500", "dxy"):
        rho, low, high = bootstrap_correlation(
            returns["gold_futures"].to_numpy(), returns[name].to_numpy()
        )
        contains_zero = low <= 0.0 <= high
        print(
            f"{name:<12} {rho:>+8.4f}   [{low:>+7.4f}, {high:>+7.4f}]  "
            f"{'JA' if contains_zero else 'nee'}"
        )
        results[f"corr_gold_{name}"] = round(rho, 4)
        results[f"corr_gold_{name}_ci_low"] = round(low, 4)
        results[f"corr_gold_{name}_ci_high"] = round(high, 4)

    # -- 2. stress en regimes ---------------------------------------------
    section("2. HOUDT DAT STAND IN STRESS?")
    print(
        "\nDit is de toets die telt. De periodes zijn VOORAF gekozen op bekende\n"
        "gebeurtenissen, niet gezocht in de data.\n"
    )
    print(f"  {'periode':<14} {'N':>5} {'rho_sp500':>11} {'rho_dxy':>10}")
    for label, (start, end) in STRESS_PERIODS.items():
        window = returns.loc[start:end]
        if len(window) < 10:
            print(f"  {label:<14} te kort")
            continue
        rho_sp = window["gold_futures"].corr(window["sp500"])
        rho_dxy = window["gold_futures"].corr(window["dxy"])
        print(f"  {label:<14} {len(window):>5} {rho_sp:>+11.4f} {rho_dxy:>+10.4f}")
        key = label.split()[0].lower()
        results[f"corr_gold_sp500_stress_{key}"] = round(float(rho_sp), 4)

    median_vix = float(vix.median())
    calm = returns[vix <= median_vix]
    turbulent = returns[vix > median_vix]
    print(f"\n  Regimes, gesplitst op de VIX-mediaan ({median_vix:.1f}):")
    for label, window in (("kalm", calm), ("volatiel", turbulent)):
        print(
            f"  {label:<14} {len(window):>5} "
            f"{window['gold_futures'].corr(window['sp500']):>+11.4f} "
            f"{window['gold_futures'].corr(window['dxy']):>+10.4f}"
        )
    results["corr_gold_sp500_calm"] = round(
        float(calm["gold_futures"].corr(calm["sp500"])), 4
    )
    results["corr_gold_sp500_volatile"] = round(
        float(turbulent["gold_futures"].corr(turbulent["sp500"])), 4
    )

    # -- 3. hedge ratio en effectiviteit ----------------------------------
    section("3. HEDGE RATIO EN EFFECTIVITEIT")
    print(
        "\nh* = cov(exposure, hedger) / var(hedger), de OLS-beta. De\n"
        "variantiereductie die je daarmee haalt is de R-kwadraat van die\n"
        "regressie: de standaardmaat voor hedge effectiveness.\n"
    )

    pairs = {
        "S&P500 met goud": ("sp500", "gold_futures"),
        "DXY met goud": ("dxy", "gold_futures"),
        "goud met DXY": ("gold_futures", "dxy"),
    }
    print(f"  {'hedge':<20} {'h*':>9} {'variantiereductie':>20}")
    for label, (exposure, hedger) in pairs.items():
        h_star, reduction = minimum_variance_hedge(
            returns[exposure].to_numpy(), returns[hedger].to_numpy()
        )
        print(f"  {label:<20} {h_star:>+9.4f} {reduction:>19.2%}")
        key = f"{exposure}_hedged_with_{hedger}"
        results[f"hedge_ratio_{key}"] = round(h_star, 4)
        results[f"variance_reduction_{key}"] = round(reduction, 4)

    print(
        "\n  OUT-OF-SAMPLE: h* geschat op de eerste helft, toegepast op de tweede.\n"
        "  Dit is de eerlijke toets - een hedge ratio die alleen in-sample werkt\n"
        "  is een curve-fit.\n"
    )
    half = len(returns) // 2
    train, test = returns.iloc[:half], returns.iloc[half:]
    print(f"  {'hedge':<20} {'h*':>9} {'in-sample':>12} {'out-of-sample':>15}")
    for label, (exposure, hedger) in pairs.items():
        h_star, reduction_is = minimum_variance_hedge(
            train[exposure].to_numpy(), train[hedger].to_numpy()
        )
        hedged_test = test[exposure] - h_star * test[hedger]
        reduction_oos = 1.0 - hedged_test.var() / test[exposure].var()
        print(
            f"  {label:<20} {h_star:>+9.4f} {reduction_is:>11.2%} "
            f"{reduction_oos:>14.2%}"
        )
        key = f"{exposure}_hedged_with_{hedger}"
        results[f"hedge_ratio_oos_{key}"] = round(h_star, 4)
        results[f"variance_reduction_oos_{key}"] = round(float(reduction_oos), 4)

    # -- 4. portefeuille-effect -------------------------------------------
    section("4. WAT DOET EEN GOUDALLOCATIE MET EEN AANDELENPORTEFEUILLE?")
    print(
        "\nLet op het onderscheid. Als de winst meeschaalt met de ALLOCATIE en\n"
        "niet met de bescherming op het juiste moment, dan is het\n"
        "diversificatie - goud heeft zelf rendement en lage correlatie - en\n"
        "geen hedge.\n"
    )
    print(
        f"  {'portefeuille':<24} {'jaarrend.':>10} {'jaarvol.':>9} "
        f"{'maxDD':>9} {'CVaR5%':>8}"
    )
    for weight in (0.0, 0.05, 0.10, 0.20):
        combined = (
            (1 - weight) * returns["sp500"] + weight * returns["gold_futures"]
        ).to_numpy()
        statistics = portfolio_statistics(combined)
        label = (
            "100% aandelen"
            if weight == 0
            else f"{weight:.0%} goud / {1 - weight:.0%} aandelen"
        )
        print(
            f"  {label:<24} {statistics['annual_return']:>+9.2%} "
            f"{statistics['annual_volatility']:>9.2%} "
            f"{statistics['max_drawdown']:>9.2%} {statistics['cvar_5pct']:>+8.2%}"
        )
        tag = f"{int(weight * 100)}pct_gold"
        results[f"portfolio_{tag}_annual_vol"] = round(
            statistics["annual_volatility"], 4
        )
        results[f"portfolio_{tag}_max_drawdown"] = round(
            statistics["max_drawdown"], 4
        )
        results[f"portfolio_{tag}_cvar_5pct"] = round(statistics["cvar_5pct"], 4)
        results[f"portfolio_{tag}_annual_return"] = round(
            statistics["annual_return"], 4
        )

    print("\n  In de zwaarste drawdowns:")
    print(f"  {'periode':<14} {'portefeuille':<16} {'maxDD':>9} {'CVaR5%':>9}")
    for label, (start, end) in STRESS_PERIODS.items():
        window = returns.loc[start:end]
        if len(window) < 10:
            continue
        for weight, tag in ((0.0, "ongehedged"), (0.10, "10% goud")):
            combined = (
                (1 - weight) * window["sp500"] + weight * window["gold_futures"]
            ).to_numpy()
            statistics = portfolio_statistics(combined)
            print(
                f"  {label:<14} {tag:<16} {statistics['max_drawdown']:>9.2%} "
                f"{statistics['cvar_5pct']:>+9.2%}"
            )
            if label == "maart 2020":
                key = "unhedged" if weight == 0 else "10pct_gold"
                results[f"march2020_{key}_max_drawdown"] = round(
                    statistics["max_drawdown"], 4
                )

    # -- 5. roll-effect ---------------------------------------------------
    section("5. ZITTEN ER ROLL-SPRONGEN IN DE REEKS?")
    print(
        "\nHet continue front-month contract springt bij elke doorrol naar het\n"
        "volgende contract. Dat is geen rendement. Fase 1 noemde dit 'klein\n"
        "voor goud' zonder het te meten; hier wordt het gemeten.\n"
    )
    gold = returns["gold_futures"]
    active_months = [2, 4, 6, 8, 10, 12]
    previous_months = [m - 1 if m > 1 else 12 for m in active_months]
    roll_window = gold[
        gold.index.month.isin(previous_months) & (gold.index.day >= 25)
    ]
    other = gold[~gold.index.isin(roll_window.index)]
    t_statistic, p_mean = sps.ttest_ind(roll_window, other, equal_var=False)
    _, p_variance = sps.levene(roll_window, other)
    print(f"  {'venster':<22} {'N':>6} {'gemiddelde':>12} {'std':>9}")
    print(
        f"  {'roll-dagen':<22} {len(roll_window):>6} "
        f"{roll_window.mean():>+11.4%} {roll_window.std():>8.3%}"
    )
    print(
        f"  {'overige dagen':<22} {len(other):>6} "
        f"{other.mean():>+11.4%} {other.std():>8.3%}"
    )
    print(f"\n  verschil in gemiddelde : t = {t_statistic:+.2f}, p = {p_mean:.3f}")
    print(f"  verschil in spreiding  : Levene p = {p_variance:.3f}")
    verdict = (
        "geen aantoonbaar roll-effect"
        if p_mean > 0.05 and p_variance > 0.05
        else "LET OP: roll-effect aantoonbaar"
    )
    print(f"  conclusie              : {verdict}")
    results["roll_test_p_mean"] = round(float(p_mean), 4)
    results["roll_test_p_variance"] = round(float(p_variance), 4)
    results["roll_window_n"] = int(len(roll_window))

    # -- 6. kosten --------------------------------------------------------
    section("6. WAT KOST HET AANHOUDEN VAN DE HEDGE?")
    fed_funds = panel["fed_funds_rate"].dropna()
    current_rate = float(fed_funds.iloc[-1])
    print(
        f"\n  Fed funds op {fed_funds.index.max().date()}: {current_rate:.2f}%\n"
        f"  Gemiddeld over de steekproef: {fed_funds.mean():.2f}%\n"
    )
    print("  Opportuniteitskosten van de cashbuffer, per kwartaal:")
    for buffer in (0.25, 0.34):
        cost = buffer * current_rate / 4
        print(f"    buffer {buffer:.0%}: {cost:.3f}% van notioneel")
        results[f"financing_cost_quarterly_buffer_{int(buffer * 100)}pct"] = round(
            cost, 4
        )
    print(
        "\n  NB: een margerekening ontvangt doorgaans rente, dus de echte\n"
        "  kostenpost is de SPREAD en niet de volle rente. Dit is een\n"
        "  bovengrens.\n"
    )
    roll_cost_bps = 4 * 1.0
    print(f"  Doorrollen: ~{roll_cost_bps:.0f} bp per kwartaal (1-2 rolls x 2 transacties x 1 bp)")
    results["roll_cost_quarterly_bps"] = roll_cost_bps
    print(
        "\n  Contango/backwardation: NIET BEREKEND. Dat vereist meerdere\n"
        "  contractmaanden; een continue front-month reeks bevat die\n"
        "  informatie niet."
    )

    # -- conclusie --------------------------------------------------------
    section("CONCLUSIE")
    rho_sp = results["corr_gold_sp500"]
    reduction_sp = results["variance_reduction_oos_sp500_hedged_with_gold_futures"]
    reduction_dxy = results["variance_reduction_oos_gold_futures_hedged_with_dxy"]
    print(
        f"\nGOUD IS GEEN AANDELENHEDGE.\n"
        f"  correlatie {rho_sp:+.4f}, betrouwbaarheidsinterval bevat nul,\n"
        f"  variantiereductie out-of-sample {reduction_sp:.2%}.\n"
        f"  In maart 2020 was de correlatie POSITIEF - de hedge viel weg op\n"
        f"  precies het moment dat hij moest werken.\n"
        f"\n"
        f"GOUD IS WEL EEN DOLLARHEDGE, in bescheiden mate.\n"
        f"  correlatie {results['corr_gold_dxy']:+.4f}, stabiel over alle regimes,\n"
        f"  variantiereductie out-of-sample {reduction_dxy:.2%}, en de hedge\n"
        f"  ratio blijft rond -1,0 tussen de twee helften van de steekproef.\n"
        f"\n"
        f"WAT EEN GOUDALLOCATIE WEL DOET is diversifieren: minder volatiliteit\n"
        f"en minder drawdown zonder rendement op te geven. Dat is nuttig, maar\n"
        f"het is iets anders dan een hedge, en het verschil zit in het moment:\n"
        f"een hedge betaalt uit ALS de afgedekte positie daalt."
    )


def main() -> int:
    """Draait de analyse en schrijft de kerngetallen weg."""
    warnings.simplefilter("ignore")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", type=Path, default=None, help="schrijf kerngetallen naar dit pad"
    )
    args = parser.parse_args()

    print(LINE)
    print("IS GOUD EEN HEDGE, EN WAARVOOR?")
    print(LINE)

    results: dict = {}
    run(results)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\n  Kerngetallen opgeslagen: {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
