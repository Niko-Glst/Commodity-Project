"""Maakt de uitlegfiguren bij drie veelgestelde vragen.

Anders dan plot_distributions.py meten deze figuren niets nieuws: ze leggen
uit wat een begrip betekent.

Gebruik:
    python scripts/uitleg_figuren.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.distributions import compute_returns  # noqa: E402
from goldmodel.viz.explain import (  # noqa: E402
    plot_margin_rule,
    plot_qq_explained,
    plot_t_versus_normal,
)
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 76


def main() -> int:
    """Genereert de drie uitlegfiguren."""
    apply_style()

    print(LINE)
    print("UITLEGFIGUREN BIJ DRIE VRAGEN")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    gold_returns = compute_returns(panel, "gold_futures")
    spot = float(panel["gold_futures"].dropna().iloc[-1])

    print("\n1. Wat betekent de rechte lijn in een QQ-plot?")
    plot_qq_explained()

    print("\n2. Wat is het verschil tussen de t-verdeling en de normale verdeling?")
    plot_t_versus_normal()

    print("\n3. Waar komt de 5-10%-vuistregel vandaan?")
    _, margin = plot_margin_rule(gold_returns, spot)

    print(f"\n{LINE}")
    print("DE CIJFERS ACHTER FIGUUR 3")
    print(LINE)
    print(f"\nGoudprijs: ${spot:,.2f} per ounce")
    print(f"Een contract (100 ounce): ${margin['contract_value']:,.0f}\n")
    print(
        "Prijsstijging die je bij een SHORT positie tegen je krijgt,\n"
        "op basis van 23 jaar historie:\n"
    )
    print(f"  {'horizon':12s} {'99%-grens':>12s} {'ergste ooit':>13s}")
    print(f"  {'-' * 12} {'-' * 12:>12s} {'-' * 13:>13s}")
    for label in margin["p99_by_horizon"]:
        p99 = margin["p99_by_horizon"][label]
        worst = margin["worst_by_horizon"][label]
        print(f"  {label:12s} {p99:>11.1f}% {worst:>12.1f}%")

    print(
        "\nLees de kolom '99%-grens' zo: in 99 van de 100 gevallen blijft de\n"
        "beweging hieronder. In 1 van de 100 is hij groter."
    )
    print(f"\nFiguren: {get_output_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
