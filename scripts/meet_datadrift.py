"""Hoeveel beweegt een resultaat mee met nieuwe data?

Waarom dit script bestaat
-------------------------
Bij de audit van 13 oktober 2026 bleek de 99%-buffer van 33,7% naar 32,6% te
zijn geschoven. Er was geen regel code veranderd - er waren drie weken data
bijgekomen.

Dat is geen fout maar een eigenschap, en wel een die je moet kennen voordat je
een getal in een paper zet. Als een resultaat met een paar weken data een
procentpunt beweegt, dan is de derde decimaal betekenisloos en moet je hem niet
rapporteren.

Dit script meet die gevoeligheid expliciet: dezelfde berekening op een reeks
oplopende einddatums.

Gebruik:
    python scripts/meet_datadrift.py
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

from goldmodel.config import ALL_SERIES, ANALYSIS_END_DATE  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.simulate import (  # noqa: E402
    SimulationSettings,
    fit_garch,
    simulate_garch,
)

LINE = "=" * 78
HORIZON_DAYS = 63

# Einddatums op kwartaalafstand, eindigend op de bevroren datum en daarna
# nog een stap verder om te laten zien wat de audit aantrof.
CUTOFF_DATES = [
    "2025-09-30",
    "2025-12-31",
    "2026-03-31",
    "2026-06-30",
    "2026-09-30",
    None,  # alles wat beschikbaar is
]


def main() -> int:
    """Meet de gevoeligheid van de kerngetallen voor de einddatum."""
    warnings.simplefilter("ignore")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--paths", type=int, default=20_000)
    args = parser.parse_args()

    print(LINE)
    print("GEVOELIGHEID VOOR DE EINDDATUM")
    print(LINE)
    print(
        f"\nDezelfde berekening, alleen een andere einddatum. Alles verder\n"
        f"identiek: seed 42, {args.paths:,} paden, dezelfde GARCH-specificatie.\n"
    )

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)

    rows = []
    for cutoff in CUTOFF_DATES:
        panel = DataLoader.build_panel(report, end_date=cutoff)
        prices = panel["gold_futures"].dropna()
        returns = np.log(prices / prices.shift(1)).dropna()

        parameters = fit_garch(returns)
        settings = SimulationSettings(
            n_paths=args.paths, horizon_days=HORIZON_DAYS, seed=42, is_short=True
        )
        simulated = simulate_garch(float(returns.mean()), parameters, settings)

        rows.append(
            {
                "einddatum": str(prices.index.max().date()),
                "N": len(returns),
                "laatste_prijs": round(float(prices.iloc[-1]), 2),
                "ann_vol_pct": round(
                    float(returns.std() * np.sqrt(252) * 100), 2
                ),
                "persistentie": round(parameters.alpha + parameters.beta, 4),
                "df": round(parameters.degrees_of_freedom, 2),
                # De conditionele variantie op de LAATSTE dag, als veelvoud
                # van het langetermijngemiddelde. Dit blijkt de buffer bijna
                # volledig te verklaren - zie de analyse onderaan.
                "vol_ratio": round(
                    parameters.last_variance / parameters.long_run_variance, 2
                ),
                "startvol_pct": round(
                    float(np.sqrt(parameters.last_variance * 252) * 100), 1
                ),
                "buffer_99_pct": round(simulated.value_at_risk(0.99) * 100, 1),
            }
        )

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))

    buffers = table["buffer_99_pct"].to_numpy()
    spread = float(buffers.max() - buffers.min())

    print(
        f"\nSPREIDING OVER DE EINDDATUMS\n"
        f"  laagste buffer    {buffers.min():.1f}%\n"
        f"  hoogste buffer    {buffers.max():.1f}%\n"
        f"  spreiding         {spread:.1f} procentpunt\n"
    )
    # Waar komt die spreiding vandaan? Niet uit de steekproef, maar uit de
    # toestand op de laatste dag.
    ratios = table["vol_ratio"].to_numpy(dtype=float)
    correlation = float(np.corrcoef(ratios, buffers)[0, 1])

    print(
        f"WAAR KOMT DIE SPREIDING VANDAAN?\n"
        f"\n"
        f"  Niet uit de steekproef. De jaarvolatiliteit over de hele reeks\n"
        f"  beweegt maar van {table['ann_vol_pct'].min():.1f}% naar "
        f"{table['ann_vol_pct'].max():.1f}%, en de persistentie\n"
        f"  blijft rond {table['persistentie'].mean():.4f}.\n"
        f"\n"
        f"  Het komt uit de CONDITIONELE variantie op de laatste dag. GARCH\n"
        f"  start de simulatie vanaf de volatiliteit van vandaag, en bij een\n"
        f"  persistentie van {table['persistentie'].mean():.4f} dooft die toestand binnen een\n"
        f"  kwartaal nauwelijks uit.\n"
        f"\n"
        f"  correlatie tussen vol_ratio en de buffer: r = {correlation:.3f}\n"
        f"  verklaarde variantie: R-kwadraat = {correlation ** 2:.3f}\n"
        f"\n"
        f"  Oftewel: {100 * correlation ** 2:.0f}% van de spreiding in de buffer komt van de\n"
        f"  startvolatiliteit, niet van wat het model over goud geleerd heeft.\n"
    )

    print(
        f"WAT DIT BETEKENT VOOR DE RAPPORTAGE\n"
        f"\n"
        f"  1. De buffer is een CONDITIONELE grootheid. '99%-buffer = 37%' is\n"
        f"     onvolledig; het hoort te zijn '37% gegeven de volatiliteit van\n"
        f"     {table['startvol_pct'].iloc[-2]:.0f}% op de startdatum'. Zonder die toestand erbij\n"
        f"     is het getal niet te interpreteren.\n"
        f"\n"
        f"  2. Een enkel kopgetal is misleidend. De bandbreedte over\n"
        f"     startcondities ({buffers.min():.0f}-{buffers.max():.0f}%) is het eerlijke antwoord, en die\n"
        f"     is veel breder dan de {spread:.0f} procentpunt die je zou raden uit\n"
        f"     modelonzekerheid alleen.\n"
        f"\n"
        f"  3. Elk gerapporteerd getal hoort een einddatum te noemen.\n"
        f"\n"
        f"  Daarom staat ANALYSIS_END_DATE = {ANALYSIS_END_DATE} vast in de config.\n"
        f"  Niet om het resultaat mooier te maken, maar om het reproduceerbaar\n"
        f"  te houden."
    )

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "rows": rows,
            "buffer_spread_pp": round(spread, 2),
            "buffer_min_pct": float(buffers.min()),
            "buffer_max_pct": float(buffers.max()),
            "frozen_end_date": ANALYSIS_END_DATE,
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n  Opgeslagen: {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
