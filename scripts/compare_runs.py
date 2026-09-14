"""Vergelijkt de huidige analyse met een eerder opgeslagen momentopname.

Waarom dit script bestaat
-------------------------
Elke keer dat je de analyse opnieuw draait komen er nieuwe handelsdagen bij en
veranderen de statistieken. De vraag is dan: is dat verandering of ruis?

Dat onderscheid is niet triviaal. Een steekproefschatting van kurtosis is zeer
variabel — één extreme dag kan hem fors verschuiven. Zonder referentiepunt
kijk je naar een getal en weet je niet of het iets betekent.

Dit script legt een momentopname vast en vergelijkt daarmee. Zo zie je per
grootheid hoeveel hij bewoog, en of dat past bij het aantal nieuwe dagen.

Gebruik:
    python scripts/compare_runs.py --save            # leg de huidige stand vast
    python scripts/compare_runs.py                   # vergelijk met de vastgelegde stand
    python scripts/compare_runs.py --save --label x  # meerdere momentopnamen
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.config import ALL_SERIES, get_cache_dir  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402

SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshots"
PRICE_COLUMNS = ("gold_futures", "silver_futures", "sp500", "dxy")
LINE = "=" * 78


@dataclass
class SeriesSnapshot:
    """Statistieken van één reeks op een moment in de tijd."""

    name: str
    n_observations: int
    first_date: str
    last_date: str
    last_price: float
    mean_daily: float
    std_daily: float
    skewness: float
    excess_kurtosis: float
    days_beyond_3sd: int
    expected_beyond_3sd: float
    t_degrees_freedom: float
    worst_day: float
    best_day: float
    worst_day_date: str


def compute_snapshot(panel: pd.DataFrame, column: str) -> SeriesSnapshot | None:
    """Berekent alle kerngrootheden voor één prijsreeks."""
    if column not in panel.columns:
        return None

    prices = panel[column].dropna()
    if len(prices) < 100:
        return None

    returns = np.log(prices / prices.shift(1)).dropna()
    z = (returns - returns.mean()) / returns.std()
    df, _, _ = sps.t.fit(returns.values)

    return SeriesSnapshot(
        name=column,
        n_observations=int(len(returns)),
        first_date=str(prices.index.min().date()),
        last_date=str(prices.index.max().date()),
        last_price=float(prices.iloc[-1]),
        mean_daily=float(returns.mean()),
        std_daily=float(returns.std()),
        skewness=float(returns.skew()),
        excess_kurtosis=float(returns.kurtosis()),
        days_beyond_3sd=int((z.abs() > 3).sum()),
        expected_beyond_3sd=float(len(returns) * 2 * (1 - sps.norm.cdf(3))),
        t_degrees_freedom=float(df),
        worst_day=float(returns.min()),
        best_day=float(returns.max()),
        worst_day_date=str(returns.idxmin().date()),
    )


def build_snapshot() -> dict:
    """Bouwt een volledige momentopname van de huidige data."""
    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)

    series = {}
    for column in PRICE_COLUMNS:
        snap = compute_snapshot(panel, column)
        if snap is not None:
            series[column] = asdict(snap)

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "panel_rows": int(len(panel)),
        "panel_columns": int(panel.shape[1]),
        "panel_last_date": str(panel.index.max().date()),
        "series": series,
    }


def snapshot_path(label: str) -> Path:
    """Geeft het pad naar een momentopname."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR / f"{label}.json"


def save_snapshot(label: str) -> Path:
    """Legt de huidige stand vast."""
    snapshot = build_snapshot()
    path = snapshot_path(label)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return path


def _format_delta(old: float, new: float, *, decimals: int = 3, pct: bool = False) -> str:
    """Formatteert een verandering met teken."""
    delta = new - old
    if pct:
        return f"{delta * 100:+.{decimals}f}"
    return f"{delta:+.{decimals}f}"


def compare(old: dict, new: dict) -> None:
    """Zet twee momentopnamen naast elkaar en licht de verschillen toe."""
    old_date = old.get("panel_last_date", "?")
    new_date = new.get("panel_last_date", "?")

    print(LINE)
    print("VERGELIJKING VAN TWEE ANALYSES")
    print(LINE)
    print(f"Vorige stand  : data tot {old_date}  (vastgelegd {old['captured_at'][:10]})")
    print(f"Huidige stand : data tot {new_date}  (vastgelegd {new['captured_at'][:10]})")

    # ---------------------------------------------------------------
    print(f"\n{LINE}\n1. HOEVEEL DATA IS ERBIJ GEKOMEN?\n{LINE}")
    rows = []
    for name, new_s in new["series"].items():
        old_s = old["series"].get(name)
        if old_s is None:
            continue
        added = new_s["n_observations"] - old_s["n_observations"]
        rows.append(
            {
                "reeks": name,
                "was": old_s["n_observations"],
                "nu": new_s["n_observations"],
                "erbij": f"{added:+d}",
                "laatste_koers_was": f"{old_s['last_price']:,.2f}",
                "laatste_koers_nu": f"{new_s['last_price']:,.2f}",
                "koers_verschil": f"{(new_s['last_price'] / old_s['last_price'] - 1) * 100:+.2f}%",
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))

    # ---------------------------------------------------------------
    print(f"\n{LINE}\n2. VERDELINGSKENMERKEN: WAS TEGENOVER NU\n{LINE}")

    for name, new_s in new["series"].items():
        old_s = old["series"].get(name)
        if old_s is None:
            continue

        added = new_s["n_observations"] - old_s["n_observations"]
        print(f"\n--- {name.replace('_', ' ').upper()}  ({added:+d} handelsdagen) ---")

        table = pd.DataFrame(
            [
                {
                    "grootheid": "gemiddeld dagrendement (%)",
                    "was": f"{old_s['mean_daily'] * 100:+.4f}",
                    "nu": f"{new_s['mean_daily'] * 100:+.4f}",
                    "verschil": _format_delta(
                        old_s["mean_daily"], new_s["mean_daily"], decimals=4, pct=True
                    ),
                },
                {
                    "grootheid": "standaardafwijking (%)",
                    "was": f"{old_s['std_daily'] * 100:.4f}",
                    "nu": f"{new_s['std_daily'] * 100:.4f}",
                    "verschil": _format_delta(
                        old_s["std_daily"], new_s["std_daily"], decimals=4, pct=True
                    ),
                },
                {
                    "grootheid": "scheefheid",
                    "was": f"{old_s['skewness']:+.4f}",
                    "nu": f"{new_s['skewness']:+.4f}",
                    "verschil": _format_delta(old_s["skewness"], new_s["skewness"], decimals=4),
                },
                {
                    "grootheid": "exces-kurtosis",
                    "was": f"{old_s['excess_kurtosis']:.4f}",
                    "nu": f"{new_s['excess_kurtosis']:.4f}",
                    "verschil": _format_delta(
                        old_s["excess_kurtosis"], new_s["excess_kurtosis"], decimals=4
                    ),
                },
                {
                    "grootheid": "dagen buiten 3 sd",
                    "was": f"{old_s['days_beyond_3sd']}",
                    "nu": f"{new_s['days_beyond_3sd']}",
                    "verschil": f"{new_s['days_beyond_3sd'] - old_s['days_beyond_3sd']:+d}",
                },
                {
                    "grootheid": "t-vrijheidsgraden",
                    "was": f"{old_s['t_degrees_freedom']:.3f}",
                    "nu": f"{new_s['t_degrees_freedom']:.3f}",
                    "verschil": _format_delta(
                        old_s["t_degrees_freedom"], new_s["t_degrees_freedom"], decimals=3
                    ),
                },
            ]
        )
        print(table.to_string(index=False))

    # ---------------------------------------------------------------
    print(f"\n{LINE}\n3. IS DIT VERANDERING OF RUIS?\n{LINE}")
    _interpret(old, new)


def _interpret(old: dict, new: dict) -> None:
    """Beoordeelt of de verschillen betekenisvol zijn.

    De vuistregel die we hier toepassen: bij n waarnemingen heeft de
    geschatte scheefheid een standaardfout van ongeveer sqrt(6/n) en de
    geschatte kurtosis ongeveer sqrt(24/n) — onder de aanname dat de data
    normaal verdeeld is.

    Die aanname klopt hier juist niet, en dat maakt de werkelijke
    standaardfouten NOG groter. De grenzen hieronder zijn dus een
    ondergrens: wat er binnen valt is zeker ruis, wat erbuiten valt is
    niet automatisch betekenisvol.
    """
    for name, new_s in new["series"].items():
        old_s = old["series"].get(name)
        if old_s is None:
            continue

        n = new_s["n_observations"]
        added = n - old_s["n_observations"]
        se_skew = np.sqrt(6.0 / n)
        se_kurt = np.sqrt(24.0 / n)

        d_skew = abs(new_s["skewness"] - old_s["skewness"])
        d_kurt = abs(new_s["excess_kurtosis"] - old_s["excess_kurtosis"])

        print(f"\n{name.replace('_', ' ')}:")
        print(f"  {added} nieuwe dagen op {n} totaal = {added / n * 100:.2f}% van de steekproef")
        print(
            f"  scheefheid bewoog {d_skew:.4f}; "
            f"standaardfout van de schatting is ~{se_skew:.4f}"
            f"  -> {'binnen de ruis' if d_skew < se_skew else 'GROTER DAN DE STANDAARDFOUT'}"
        )
        print(
            f"  kurtosis bewoog {d_kurt:.4f}; "
            f"standaardfout van de schatting is ~{se_kurt:.4f}"
            f"  -> {'binnen de ruis' if d_kurt < se_kurt else 'GROTER DAN DE STANDAARDFOUT'}"
        )

        if new_s["worst_day_date"] != old_s["worst_day_date"]:
            print(
                f"  LET OP: de slechtste dag is veranderd van "
                f"{old_s['worst_day_date']} naar {new_s['worst_day_date']}"
            )


def main() -> int:
    """Slaat op of vergelijkt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="leg de huidige stand vast")
    parser.add_argument("--label", default="baseline", help="naam van de momentopname")
    parser.add_argument("--against", default="baseline", help="waarmee vergelijken")
    args = parser.parse_args()

    pd.set_option("display.width", 140)

    if args.save:
        path = save_snapshot(args.label)
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        print(f"Momentopname '{args.label}' opgeslagen: {path}")
        print(f"Data tot {snapshot['panel_last_date']}, {len(snapshot['series'])} reeksen.")
        return 0

    old_path = snapshot_path(args.against)
    if not old_path.exists():
        print(f"Geen momentopname '{args.against}' gevonden in {SNAPSHOT_DIR}")
        print("Leg er eerst een vast met: python scripts/compare_runs.py --save")
        return 1

    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = build_snapshot()
    compare(old, new)

    print(f"\n{LINE}")
    print(f"Cache: {get_cache_dir()}")
    print("Wil je deze stand vastleggen als nieuwe referentie?")
    print("  python scripts/compare_runs.py --save")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
