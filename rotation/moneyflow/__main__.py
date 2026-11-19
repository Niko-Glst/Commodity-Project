"""Command line (run from rotation/):

    python -m moneyflow check      # fresh data, print where money is moving (no files written except data/)
    python -m moneyflow report     # results.json + PDF in reports/<last close>/ (needs external.json there)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import analysis as A
from . import data

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def collect(p: pd.DataFrame, c: pd.DataFrame, fred: dict) -> dict:
    perf = A.performance(p)
    pos = A.positioning(c)
    return {
        "last_close": str(p.index[-1].date()),
        "performance": json.loads(perf.reset_index(names="ticker").to_json(orient="records")),
        "profit_taking": A.profit_taking(perf),
        "beat_cash": {k: A.beat_cash(perf, k) for k in ("since_peak", "november", "last_week")},
        "positioning": json.loads(pos.to_json(orient="records", date_format="iso")),
        "m2": float(fred["M2SL"].iloc[-1]), "m2_date": str(fred["M2SL"].index[-1].date()),
        "rrp": float(fred["RRPONTSYD"].iloc[-1]), "rrp_date": str(fred["RRPONTSYD"].index[-1].date()),
    }


def cot_evidence(pos: pd.DataFrame) -> list[list[str]]:
    d = pd.Timestamp(pos.date.iloc[0])
    r = pos.set_index("series")
    g, cu, nq = r.loc["Gold"], r.loc["Copper"], r.loc["Nasdaq-100 (mini), leveraged"]
    return [
        [f"Speculators in gold (CFTC, {d.day} {d:%b})", f"Managed money net long {g.net:,.0f} contracts, {g.chg_1w:+,.0f} on "
         "the week", "Still adding before this week's drop" if g.chg_1w > 0 else "Cutting gold"],
        [f"Speculators in copper (CFTC, {d.day} {d:%b})", f"Net long {cu.net:,.0f}; {cu.chg_4w:+,.0f} over four weeks",
         "Cutting copper" if cu.chg_4w < 0 else "Adding copper"],
        [f"Hedge funds in Nasdaq-100 futures (CFTC, {d.day} {d:%b})",
         f"Leveraged funds net long {nq.net:,.0f}; {nq.chg_4w:+,.0f} over four weeks, {nq.range_pct:.0%} of the range since 2024",
         "Bought the dip" if nq.chg_4w > 0 else "Sold"],
    ]


def cmd_check(args) -> None:
    p, c, fred = data.load(refresh=not args.cached)
    perf = A.performance(p)
    pt = A.profit_taking(perf)
    print(f"Prices to {p.index[-1]:%Y-%m-%d} close. Cash = {A.CASH} (1-3 month T-bills).\n")
    for col, label in (("last_week", "Last 7 days"), ("november", "November"), ("since_peak", f"Since {A.PEAK}")):
        n, tot = A.beat_cash(perf, col)
        x = perf.sort_values(col)
        print(f"{label}: {n} of {tot} assets beat cash ({perf.loc[A.CASH, col]:+.2%}).")
        print("  weakest: " + ", ".join(f"{r['name']} {r[col]:+.1%}" for _, r in x.head(4).iterrows()))
        print("  strongest: " + ", ".join(f"{r['name']} {r[col]:+.1%}" for _, r in x.tail(4).iloc[::-1].iterrows()))
    print(f"\nProfit-taking test: rank correlation of 12-month gain to {A.PEAK} with the move since = "
          f"{pt['spearman']:+.2f} (p = {pt['p']:.3f}); negative = winners sold hardest.")
    print("\nFutures positioning (CFTC):")
    with pd.option_context("display.width", 160, "display.float_format", "{:,.0f}".format):
        print(A.positioning(c).drop(columns=["net_pct_oi"]).assign(range_pct=lambda d: (d.range_pct * 100).round())
              .to_string(index=False))
    print(f"\nFed reverse repo {fred['RRPONTSYD'].iloc[-1]:,.1f} $bn ({fred['RRPONTSYD'].index[-1]:%Y-%m-%d}); "
          f"M2 {fred['M2SL'].iloc[-1]:,.0f} $bn ({fred['M2SL'].index[-1]:%Y-%m})")
    print("\nNot automated (check by hand): ICI money funds (Thu 16:30 ET), ETF.com weekly flows, "
          "BofA fund manager survey (mid-month).")


def cmd_report(args) -> None:
    from .report import build_pdf

    p, c, fred = data.load()
    out = collect(p, c, fred)
    folder = REPORTS / out["last_close"]
    ext = json.loads((folder / "external.json").read_text(encoding="utf-8"))
    ext["evidence"] = ext["evidence"] + cot_evidence(pd.DataFrame(out["positioning"]))
    out["external"] = ext
    (folder / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {build_pdf(p, c, folder)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="moneyflow")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check", help="print where money is moving")
    s.add_argument("--cached", action="store_true", help="use the saved snapshot instead of downloading")
    s.set_defaults(func=cmd_check)
    sub.add_parser("report", help="write results.json and the PDF").set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
