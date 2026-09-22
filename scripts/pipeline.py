"""Eén commando dat de hele analyse draait, reproduceerbaar.

Elke run krijgt een run-ID en een seed, en schrijft een manifest weg met alles
wat nodig is om het resultaat te reproduceren: de seed, de datastand, de
pakketversies en de git-commit.

Gebruik:
    python scripts/pipeline.py                      # volledige run
    python scripts/pipeline.py --seed 123           # andere seed
    python scripts/pipeline.py --stage backtest     # één onderdeel
    python scripts/pipeline.py --snel               # minder herhalingen
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.backtest import (  # noqa: E402
    CostModel,
    compare_to_benchmarks,
    placebo_backtest,
    run_backtest,
    sharpe_significance,
)
from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.models import walk_forward_validate  # noqa: E402
from goldmodel.signal import (  # noqa: E402
    SignalSettings,
    position_statistics,
    predictions_to_positions,
)
from goldmodel.simulate import (  # noqa: E402
    SimulationSettings,
    fit_garch,
    simulate_garch,
)
from goldmodel.viz.correlations import build_change_panel  # noqa: E402
from goldmodel.viz.distributions import compute_returns  # noqa: E402

LINE = "=" * 78

DRIVERS = [
    "real_rate_10y",
    "usd_broad_index",
    "breakeven_inflation_10y",
    "vix",
]


@dataclass
class RunManifest:
    """Alles wat nodig is om een run te reproduceren.

    Waarom dit bestaat: een resultaat zonder manifest is niet na te rekenen.
    De seed bepaalt de Monte Carlo, de datastand bepaalt de input, en de
    git-commit bepaalt de code. Ontbreekt er één, dan kun je een getal niet
    terugvinden.
    """

    run_id: str
    started_at: str
    seed: int
    git_commit: str
    python_version: str
    platform: str
    data_last_date: str
    n_observations: int
    package_versions: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)

    def save(self, directory: Path) -> Path:
        """Schrijft het manifest weg als JSON."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.json"
        path.write_text(
            json.dumps(asdict(self), indent=2, default=str), encoding="utf-8"
        )
        return path


def current_commit() -> str:
    """Geeft de huidige git-commit terug, of 'onbekend'."""
    for candidate in ("git", r"C:\Program Files\Git\cmd\git.exe"):
        try:
            result = subprocess.run(
                [candidate, "rev-parse", "--short", "HEAD"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
    return "onbekend"


def package_versions() -> dict:
    """Versies van de pakketten die de uitkomst bepalen."""
    versions = {}
    for name in ("pandas", "numpy", "statsmodels", "arch", "scipy", "sklearn"):
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "onbekend")
        except ImportError:
            versions[name] = "niet geïnstalleerd"
    return versions


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def stage_signal_and_backtest(
    changes: pd.DataFrame, returns: pd.Series, *, seed: int
) -> dict:
    """Bouwt een positie uit het model en rekent hem door na kosten."""
    section("SIGNAAL EN BACKTEST")

    print(
        "\nWAARSCHUWING VOORAF\n"
        "Fase 3 heeft al gemeten dat dit signaal geen voorspelkracht heeft:\n"
        "directional accuracy 43,8%, out-of-sample R-kwadraat -0,04.\n"
        "\n"
        "Deze backtest bouwt er toch een strategie op. Niet omdat dat kansrijk\n"
        "is, maar omdat het de bevinding KWANTIFICEERT: hoeveel geld kost het\n"
        "om te handelen op een signaal dat er niet is?\n"
        "\n"
        "Dat is een zinvolle uitkomst. Het is alleen iets anders dan een\n"
        "strategie."
    )

    available = [d for d in DRIVERS if d in changes.columns]
    target = changes["gold_futures"]

    # horizon EN step op 21: zo voorspelt elk venster 21 aaneengesloten dagen
    # en schuift daarna precies door. Met horizon=1 en step=21 zou je per
    # venster een enkele dag voorspellen en twintig overslaan - dan houd je
    # een paar honderd losse dagen over in plaats van een doorlopende reeks,
    # en kun je geen positie backtesten.
    #
    # Het model wordt dus elke maand opnieuw geschat en gebruikt die maand.
    walk_forward = walk_forward_validate(
        target, changes[available], min_train=1000, horizon=21, step=21
    )
    predictions = walk_forward.predictions["ols"]

    settings = SignalSettings(method="linear", max_position=1.0)
    positions = predictions_to_positions(predictions, settings)

    stats = position_statistics(positions)
    print(
        f"\nPOSITIE\n"
        f"  handelsdagen               {stats['n_days']}\n"
        f"  dagen met positie          {stats['n_days_in_market']} "
        f"({stats['share_in_market']:.0%})\n"
        f"  gemiddelde |positie|       {stats['mean_abs_position']:.3f}\n"
        f"  omzet per jaar             {stats['annual_turnover']:.1f}x"
    )

    cost_model = CostModel()
    result = run_backtest(
        positions, returns, cost_model=cost_model, execution_lag=1
    )

    print(
        f"\nUITVOERING\n"
        f"  executie-lag               {result.execution_lag} dag "
        "(positie van vandaag gaat morgen in)\n"
        f"  kosten per transactie      {cost_model.total_bps:.1f} bp "
        f"(commissie {cost_model.commission_bps}, spread "
        f"{cost_model.half_spread_bps}, slippage {cost_model.slippage_bps})"
    )

    table = compare_to_benchmarks(result, returns)
    display = table[
        ["n", "annual_return", "annual_volatility", "sharpe", "max_drawdown"]
    ].copy()
    display["annual_return"] = display["annual_return"].map(lambda v: f"{v:+.2%}")
    display["annual_volatility"] = display["annual_volatility"].map(
        lambda v: f"{v:.2%}"
    )
    display["sharpe"] = display["sharpe"].map(lambda v: f"{v:+.3f}")
    display["max_drawdown"] = display["max_drawdown"].map(lambda v: f"{v:.1%}")
    print(f"\nRESULTAAT\n\n{display.to_string()}")

    significance = sharpe_significance(result.net_returns)
    print(
        f"\nIS DIE SHARPE IETS?\n"
        f"  Sharpe (netto)             {significance['sharpe']:+.3f}\n"
        f"  standaardfout              {significance['standard_error']:.3f}\n"
        f"  t-waarde                   {significance['t_statistic']:+.2f}\n"
        f"  significant?               "
        f"{'JA' if significance['significant'] else 'NEE'}\n"
        f"\n"
        f"  Bij {significance['years']:.1f} jaar data is een Sharpe van minstens\n"
        f"  {significance['sharpe_needed_for_significance']:.2f} nodig om van nul "
        "te onderscheiden.\n"
        "\n"
        "  Dit getal hoort bij ELKE gerapporteerde Sharpe en ontbreekt in de\n"
        "  meeste backtests."
    )

    placebo = placebo_backtest(
        positions, returns, n_trials=200, seed=seed, cost_model=cost_model
    )
    print(
        f"\nPLACEBO (posities door de tijd geschud, {placebo['n_trials']} keer)\n"
        f"  echte Sharpe               {placebo['real_sharpe']:+.3f}\n"
        f"  placebo mediaan            {placebo['placebo_median']:+.3f}\n"
        f"  placebo 95e percentiel     {placebo['placebo_p95']:+.3f}\n"
        f"  echte uitkomst op het      {placebo['percentile_of_real']:.0f}e percentiel\n"
        f"  te onderscheiden?          "
        f"{'JA' if placebo['distinguishable'] else 'NEE'}"
    )

    gross = result.metrics["gross"]
    net = result.metrics["net"]
    print(
        f"\nWAT DE KOSTEN DOEN\n"
        f"  bruto jaarrendement        {gross['annual_return']:+.2%}\n"
        f"  netto jaarrendement        {net['annual_return']:+.2%}\n"
        f"  kostenlast per jaar        {result.metrics['cost_drag_annual']:.2%}"
    )

    return {
        "n_days": stats["n_days"],
        "annual_turnover": stats["annual_turnover"],
        "gross_sharpe": gross["sharpe"],
        "net_sharpe": net["sharpe"],
        "net_annual_return": net["annual_return"],
        "max_drawdown": net["max_drawdown"],
        "sharpe_significant": significance["significant"],
        "sharpe_hurdle": significance["sharpe_needed_for_significance"],
        "placebo_percentile": placebo["percentile_of_real"],
        "placebo_distinguishable": placebo["distinguishable"],
        "cost_drag_annual": result.metrics["cost_drag_annual"],
    }


def stage_margin(returns: pd.Series, spot: float, *, seed: int) -> dict:
    """Draait de margeberekening, het eigenlijke doel van het project."""
    section("MARGEBEHOEFTE (HET DOEL VAN HET PROJECT)")

    parameters = fit_garch(returns)
    settings = SimulationSettings(
        n_paths=20_000, horizon_days=63, seed=seed, is_short=True
    )
    simulated = simulate_garch(float(returns.mean()), parameters, settings)

    var99 = simulated.value_at_risk(0.99)
    expected_shortfall = simulated.expected_shortfall(0.99)
    notional = spot * 100

    print(
        f"\n  goudprijs                  ${spot:,.2f}\n"
        f"  notioneel per contract     ${notional:,.0f}\n"
        f"  paden                      {settings.n_paths:,}\n"
        f"  seed                       {settings.seed}\n"
        f"\n"
        f"  99%-buffer                 {var99:.1%} (${var99 * notional:,.0f})\n"
        f"  Expected Shortfall         {expected_shortfall:.1%}\n"
        f"  5%-regel dekt              {float((simulated.max_adverse <= 0.05).mean()):.1%}\n"
        f"  10%-regel dekt             {float((simulated.max_adverse <= 0.10).mean()):.1%}"
    )

    return {
        "var_99": float(var99),
        "expected_shortfall_99": float(expected_shortfall),
        "notional": float(notional),
        "garch_persistence": float(parameters.persistence),
    }


def main() -> int:
    """Draait de pijplijn."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 170)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="toevalszaad")
    parser.add_argument(
        "--stage",
        choices=("alles", "backtest", "marge"),
        default="alles",
        help="welk onderdeel",
    )
    parser.add_argument("--snel", action="store_true", help="minder herhalingen")
    args = parser.parse_args()

    np.random.seed(args.seed)
    run_id = f"run_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_seed{args.seed}"

    print(LINE)
    print("GOUDPRIJS-RISICOMODEL — VOLLEDIGE PIJPLIJN")
    print(LINE)
    print(f"\n  run-ID   {run_id}")
    print(f"  seed     {args.seed}")
    print(f"  commit   {current_commit()}")

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    prices = panel["gold_futures"].dropna()
    returns = compute_returns(panel, "gold_futures")
    changes = build_change_panel(panel)

    manifest = RunManifest(
        run_id=run_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        seed=args.seed,
        git_commit=current_commit(),
        python_version=platform.python_version(),
        platform=platform.platform(),
        data_last_date=str(prices.index.max().date()),
        n_observations=int(len(returns)),
        package_versions=package_versions(),
    )

    print(f"  data tot {manifest.data_last_date}")
    print(f"  N        {manifest.n_observations:,} handelsdagen")

    if args.stage in ("alles", "backtest"):
        manifest.results["backtest"] = stage_signal_and_backtest(
            changes, returns, seed=args.seed
        )

    if args.stage in ("alles", "marge"):
        manifest.results["margin"] = stage_margin(
            returns, float(prices.iloc[-1]), seed=args.seed
        )

    path = manifest.save(PROJECT_ROOT / "output" / "runs")

    section("REPRODUCEERBAARHEID")
    print(
        f"\n  Manifest opgeslagen: {path.name}\n"
        f"  Bevat seed, git-commit, pakketversies en datastand.\n"
        f"\n"
        f"  Deze run exact herhalen:\n"
        f"    python scripts/pipeline.py --seed {args.seed}\n"
        f"\n"
        f"  Let op: de DATA verandert als je opnieuw ophaalt. Het manifest\n"
        f"  legt vast tot welke datum de reeks liep, zodat een afwijkend\n"
        f"  resultaat te herleiden is naar nieuwe data in plaats van naar\n"
        f"  toeval."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
