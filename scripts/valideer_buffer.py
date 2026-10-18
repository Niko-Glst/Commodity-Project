"""Valideert de kernclaim: verslaat een GARCH-t buffer een vuistregel?

Draait de dekkingstoetsen op vier bufferregels en rapporteert welke wint op
dekking EN kapitaalefficiëntie. Plus een gevoeligheidsanalyse op de
vrijheidsgraden.

Gebruik:
    python scripts/valideer_buffer.py
    python scripts/valideer_buffer.py --snel   # minder paden
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.simulate import (  # noqa: E402
    GarchParameters,
    SimulationSettings,
    fit_garch,
    simulate_garch,
)
from goldmodel.validation import (  # noqa: E402
    compare_buffer_rules,
    ewma_buffer,
    fixed_buffer,
    rolling_percentile_buffer,
)
from goldmodel.viz.distributions import compute_returns  # noqa: E402

LINE = "=" * 78
HORIZON_DAYS = 63
# Evenveel paden als de hoofdsimulatie en de backtest in freeze_results.py.
N_PATHS = 20_000
CONFIDENCE = 0.99


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def build_quarter_starts(returns: pd.Series, *, min_history: int = 1000) -> pd.Index:
    """De startdatums van niet-overlappende kwartalen.

    Niet-overlappend is essentieel: overlappende vensters delen data en zijn
    dus niet onafhankelijk. De Christoffersen-toets neemt onafhankelijkheid
    aan, dus overlappende vensters zouden hem betekenisloos maken.
    """
    values = returns.dropna()
    positions = range(min_history, len(values) - HORIZON_DAYS, HORIZON_DAYS)
    return pd.Index([values.index[p] for p in positions])


def realised_excursions(returns: pd.Series, starts: pd.Index) -> pd.Series:
    """De werkelijk opgetreden tegenbeweging per kwartaal.

    Voor een short positie: de grootste tussentijdse STIJGING, want daar komt
    de margin call.
    """
    values = returns.dropna()
    outcomes = {}
    for start in starts:
        position = values.index.get_loc(start)
        window = values.iloc[position : position + HORIZON_DAYS].to_numpy()
        if len(window) < HORIZON_DAYS:
            continue
        path = np.concatenate([[0.0], np.cumsum(window)])
        outcomes[start] = float(np.expm1(path.max()))
    return pd.Series(outcomes, name="realised").sort_index()


def garch_buffers(
    returns: pd.Series, starts: pd.Index, *, n_paths: int, seed: int
) -> pd.Series:
    """De GARCH-t buffer, opnieuw geschat op elk beslismoment.

    Dit is de eerlijke opzet: op elk kwartaalbegin wordt het model geschat op
    ALLEEN de data die dan beschikbaar was, en daarmee de buffer voor het
    komende kwartaal bepaald.
    """
    values = returns.dropna()
    buffers = {}

    for index, start in enumerate(starts):
        history = values.loc[values.index < start]
        if len(history) < 500:
            continue
        try:
            parameters = fit_garch(history)
            settings = SimulationSettings(
                n_paths=n_paths,
                horizon_days=HORIZON_DAYS,
                seed=seed + index,
                is_short=True,
            )
            simulated = simulate_garch(float(history.mean()), parameters, settings)
            buffers[start] = simulated.value_at_risk(CONFIDENCE)
        except Exception:  # noqa: BLE001 - GARCH convergeert niet altijd
            continue

    return pd.Series(buffers, name="garch_t").sort_index()


def run_coverage_comparison(returns: pd.Series, *, n_paths: int, seed: int) -> None:
    """P1: vergelijkt GARCH-t met drie naïeve alternatieven."""
    section("P1: VERSLAAT GARCH-t DE VUISTREGELS?")

    starts = build_quarter_starts(returns)
    realised = realised_excursions(returns, starts)

    print(
        f"\nOPZET\n"
        f"  horizon                    {HORIZON_DAYS} handelsdagen (een kwartaal)\n"
        f"  dekkingsniveau             {CONFIDENCE:.0%}\n"
        f"  niet-overlappende kwartalen {len(realised)}\n"
        f"\n"
        f"  Niet-overlappend is essentieel: overlappende vensters delen data,\n"
        f"  en dan is de onafhankelijkheidstoets betekenisloos."
    )

    print("\nDe vier regels:\n")
    print("  garch_t       GARCH(1,1) met t-schokken, opnieuw geschat per kwartaal")
    print("  vast_25pct    een vaste buffer van 25%, ongeacht de markt")
    print("  rolling_p99   het 99e percentiel van de afgelopen twee jaar")
    print("  ewma_094      RiskMetrics: EWMA-volatiliteit, normale staarten")

    print("\nBuffers berekenen (GARCH duurt even, per kwartaal opnieuw schatten)...")

    rules = {
        "garch_t": garch_buffers(returns, starts, n_paths=n_paths, seed=seed),
        "vast_25pct": fixed_buffer(starts, level=0.25),
        "rolling_p99": rolling_percentile_buffer(
            returns, starts, horizon_days=HORIZON_DAYS, confidence=CONFIDENCE
        ),
        "ewma_094": ewma_buffer(
            returns, starts, horizon_days=HORIZON_DAYS, confidence=CONFIDENCE
        ),
    }

    table, results = compare_buffer_rules(rules, realised, confidence=CONFIDENCE)

    print(f"\n{'=' * 78}\nRESULTAAT\n{'=' * 78}\n")
    print(table.to_string(index=False))

    print(
        "\nKOLOMMEN\n"
        "  breaches          hoe vaak de buffer doorbroken werd\n"
        "  expected          hoeveel er verwacht werden bij 99%\n"
        "  kupiec_p          toetst of het AANTAL klopt\n"
        "  christoffersen_p  toetst of de overschrijdingen ONAFHANKELIJK zijn\n"
        "  mean_buffer       gemiddelde buffergrootte (kapitaalefficiëntie)\n"
        "  underpowered      heeft de toets genoeg kracht om iets af te wijzen?"
    )

    # De cruciale waarschuwing.
    first = next(iter(results.values()))
    print(
        f"\n{'!' * 78}\n"
        f"KRACHT VAN DE TOETS\n"
        f"{'!' * 78}\n"
        f"\n"
        f"Bij {first.n_periods} kwartalen en een drempel van {CONFIDENCE:.0%} verwacht je\n"
        f"{first.expected_breaches:.2f} overschrijdingen.\n"
        f"\n"
        f"Met minder dan een handvol verwachte gebeurtenissen kan GEEN ENKELE\n"
        f"toets onderscheid maken. Een model met 0 overschrijdingen en een met\n"
        f"3 zijn allebei verenigbaar met de nulhypothese.\n"
        f"\n"
        f"Elke p-waarde in de tabel hierboven is dus indicatief, niet\n"
        f"beslissend. Dat is een beperking van 23 jaar data op kwartaalhorizon,\n"
        f"niet van de opzet."
    )

    # Wie wint, op beide criteria?
    print(f"\n{'=' * 78}\nWIE WINT?\n{'=' * 78}")

    passing = {
        label: result
        for label, result in results.items()
        if not result.kupiec_rejects and not result.christoffersen_rejects
    }

    print(f"\nRegels die BEIDE toetsen halen: {', '.join(passing) or 'geen'}")

    if passing:
        cheapest = min(passing.values(), key=lambda r: r.mean_buffer)
        print(
            f"\nDaarvan de laagste gemiddelde buffer: "
            f"{cheapest.label} ({cheapest.mean_buffer:.1%})"
        )

        garch = results.get("garch_t")
        if garch is not None and cheapest.label != "garch_t":
            print(
                f"\n  GARCH-t WINT NIET. {cheapest.label} haalt dezelfde dekking\n"
                f"  met een buffer van {cheapest.mean_buffer:.1%} tegenover\n"
                f"  {garch.mean_buffer:.1%} voor GARCH-t.\n"
                f"\n"
                f"  Dat is het resultaat. Ik pas de parameters niet aan tot\n"
                f"  GARCH wel wint - dan zou ik mijn eigen keuzevrijheid meten\n"
                f"  in plaats van het model."
            )
        elif garch is not None:
            print(
                f"\n  GARCH-t wint op beide criteria. Let wel op de kracht van\n"
                f"  de toets hierboven: 'haalt de toets' betekent hier vooral\n"
                f"  'wordt niet afgewezen', en dat lukt bijna elk model bij\n"
                f"  {first.expected_breaches:.1f} verwachte overschrijdingen."
            )

    print("\nOVERSCHRIJDINGEN PER REGEL:")
    for label, result in results.items():
        if result.breach_dates:
            print(f"  {label:14s} {', '.join(result.breach_dates)}")
        else:
            print(f"  {label:14s} geen")


def run_df_sensitivity(returns: pd.Series, *, n_paths: int, seed: int) -> None:
    """P2: hoeveel van de bandbreedte komt door de df-onzekerheid?"""
    section("P2: HOE GEVOELIG IS DE BUFFER VOOR DE VRIJHEIDSGRADEN?")

    parameters = fit_garch(returns)
    print(
        f"\nDE SCHATTING\n"
        f"  df (MLE, samen met GARCH)  {parameters.degrees_of_freedom:.3f}\n"
        f"  standaardfout              {parameters.degrees_of_freedom_se:.3f}\n"
        f"  95%-interval               "
        f"[{parameters.degrees_of_freedom - 1.96 * parameters.degrees_of_freedom_se:.2f}, "
        f"{parameters.degrees_of_freedom + 1.96 * parameters.degrees_of_freedom_se:.2f}]\n"
    )
    print(
        "WAAROM DIT ANDERS IS DAN DE QQ-PLOT\n"
        "De QQ-fit op ruwe rendementen gaf 3,54. Die ziet de dikke staarten van\n"
        "CLUSTERING en van echte STAARTDIKTE door elkaar.\n"
        "\n"
        "De MLE haalt de clustering er eerst uit via het GARCH-deel; wat\n"
        "overblijft is de staartdikte van de schokken zelf. Die is dunner.\n"
        "\n"
        "Dat verschil is materieel: onder df = 4 is de populatiekurtosis\n"
        "ONEINDIG. Met 3,54 zat het model in dat gebied, met 4,80 er net boven.\n"
        "Het 95%-interval [4,21 - 5,39] ligt volledig boven 4."
    )

    # De gevoeligheidstabel krijgt ALTIJD veel paden, ook met --snel. Bij 2.000
    # paden is de Monte Carlo-ruis (~2 procentpunt) groter dan het effect dat we
    # willen meten (~2 procentpunt over het hele df-bereik). Dan meet je je eigen
    # toevalsgenerator. Zie de monotoniecontrole onderaan.
    sensitivity_paths = max(n_paths, 100_000)

    print(f"\nGEVOELIGHEIDSTABEL  (n_paths = {sensitivity_paths:,})\n")
    rows = []
    for df in (3.0, 3.5, 4.0, 4.21, 4.802, 5.0, 5.39, 6.0, 8.0):
        variant = GarchParameters(
            omega=parameters.omega,
            alpha=parameters.alpha,
            beta=parameters.beta,
            degrees_of_freedom=df,
            last_variance=parameters.last_variance,
            long_run_variance=parameters.long_run_variance,
        )
        # Zelfde zaad voor elke df: common random numbers. Het VERSCHIL tussen
        # rijen is dan een df-effect en niet twee verschillende trekkingen.
        settings = SimulationSettings(
            n_paths=sensitivity_paths,
            horizon_days=HORIZON_DAYS,
            seed=seed,
            is_short=True,
        )
        simulated = simulate_garch(float(returns.mean()), variant, settings)
        if abs(df - round(parameters.degrees_of_freedom, 3)) < 0.01:
            note = "MLE-schatting"
        elif abs(df - 4.21) < 0.01 or abs(df - 5.39) < 0.01:
            note = "grens 95%-interval"
        else:
            note = ""
        rows.append(
            {
                "df": df,
                "buffer_99pct": round(simulated.value_at_risk(0.99) * 100, 1),
                "ES_99pct": round(simulated.expected_shortfall(0.99) * 100, 1),
                "kurtosis": "oneindig" if df <= 4 else f"{6 / (df - 4):.1f}",
                "opmerking": note,
            }
        )
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))

    # Monotoniecontrole. Dikkere staarten (lagere df) horen een GROTERE buffer
    # te geven. Is de volgorde omgekeerd, dan is de Monte Carlo-ruis groter dan
    # het effect en mag je geen enkele conclusie uit de tabel trekken.
    buffers = table["buffer_99pct"].to_numpy()
    violations = int((np.diff(buffers) > 0).sum())

    within = table[(table["df"] >= 4.21) & (table["df"] <= 5.39)]
    df_spread = float(within["buffer_99pct"].max()) - float(
        within["buffer_99pct"].min()
    )
    full_spread = float(buffers.max()) - float(buffers.min())
    model_spread = 34.5 - 26.0  # GBM-normaal tegenover GARCH-t, uit fase 4

    print("\nMONOTONIECONTROLE")
    if violations:
        print(
            f"  {violations} van de {len(buffers) - 1} stappen loopt de verkeerde\n"
            f"  kant op. Dikkere staarten HOREN een grotere buffer te geven; dat\n"
            f"  ze dat hier niet doen betekent dat de ruis groter is dan het\n"
            f"  effect. Trek geen conclusie uit deze tabel - verhoog n_paths."
        )
    else:
        print(
            "  In orde: de buffer daalt monotoon met df. Het gemeten effect is\n"
            "  dus groter dan de simulatieruis."
        )

    print(
        f"\nHOEVEEL VAN DE BANDBREEDTE IS DF-ONZEKERHEID?\n"
        f"\n"
        f"  binnen 95%-interval df [4,21 - 5,39]   {df_spread:4.1f} pp\n"
        f"  over het HELE bereik df [3 - 8]        {full_spread:4.1f} pp\n"
        f"  modelkeuze (GBM-normaal - GARCH-t)     {model_spread:4.1f} pp\n"
        f"\n"
        f"  Zelfs als je df helemaal naar 3 duwt - ruim buiten het\n"
        f"  betrouwbaarheidsinterval, en in het gebied waar de populatie-\n"
        f"  kurtosis oneindig is - beweegt de buffer maar {full_spread:.1f} procentpunt.\n"
        f"  De keuze tussen constante volatiliteit en GARCH beweegt hem\n"
        f"  {model_spread:.1f} procentpunt.\n"
        f"\n"
        f"  CONCLUSIE: modelonzekerheid domineert, met een factor\n"
        f"  {model_spread / full_spread:.0f} ongeveer. De 26-34% bandbreedte komt vrijwel\n"
        f"  volledig van de modelkeuze, niet van de df-schatting.\n"
        f"\n"
        f"  Dat is geruststellend: df is geschat met een standaardfout van\n"
        f"  {parameters.degrees_of_freedom_se:.2f}, en juist die onzekerheid blijkt er nauwelijks\n"
        f"  toe te doen."
    )


def main() -> int:
    """Draait de validatie."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 200)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snel", action="store_true", help="minder paden")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    n_paths = 2_000 if args.snel else N_PATHS

    print(LINE)
    print("VALIDATIE VAN DE KERNCLAIM")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    returns = compute_returns(panel, "gold_futures")

    print(f"\n  N = {len(returns):,} handelsdagen")
    print(f"  seed = {args.seed}, paden per simulatie = {n_paths:,}")

    run_coverage_comparison(returns, n_paths=n_paths, seed=args.seed)
    run_df_sensitivity(returns, n_paths=n_paths, seed=args.seed)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
