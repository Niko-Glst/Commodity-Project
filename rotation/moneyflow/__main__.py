"""Command line (run from rotation/):

    python -m moneyflow check      # fresh data; prints flows, stress, rates and prices (writes data/ only)
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


def _records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _clean(d: dict) -> dict:
    return json.loads(pd.Series(d).to_json(date_format="iso", default_handler=str))


def collect(b) -> dict:
    perf = A.performance(b.prices)
    return {
        "last_close": str(b.prices.index[-1].date()),
        "performance": json.loads(perf.reset_index(names="ticker").to_json(orient="records")),
        "profit_taking": A.profit_taking(perf),
        "robustness": _records(A.robustness(b.prices)),
        "groups_by_start": _records(A.groups_by_start(b.prices)),
        "beat_cash": {k: A.beat_cash(perf, k) for k in ("since_peak", "november", "last_week")},
        "positioning": _records(A.positioning(b.cot)),
        "credit_and_rates": _records(A.credit_and_rates(b.fred_series)),
        "stress": _clean(A.stress(b.market, b.prices)),
        "factors": _clean(A.factors(b.market)),
        "etf_flows": _records(A.etf_flows(b.flows)),
        "mmf": _clean(A.mmf_stats(b.mmf)),
        "net_liquidity": _clean(A.net_liquidity(b.fred_series)),
    }


def cmd_check(args) -> None:
    b = data.load(refresh=not args.cached)
    R = collect(b)
    pd.set_option("display.width", 200)
    print(f"Data to {R['last_close']} (credit and rates may end a day earlier).\n")
    print("1. Credit and rates (widening spreads = real risk-off)")
    cr = pd.DataFrame(R["credit_and_rates"])
    print(cr[["series", "date", "now", "chg_peak_bp", "chg_1w_bp", "z_1w", "pct_since_2024"]].round(2).to_string(index=False))
    s = R["stress"]
    print(f"\n2. Stress: VIX/VIX3M {s['ratio']:.3f} (inverted on {', '.join(s['inverted_days_recent']) or 'no day'} in Nov), "
          f"MOVE {s['move']:.0f}, sector correlation {s['corr']:.2f} (at peak {s['corr_peak']:.2f}), "
          f"dispersion at {s['disp_pct']:.0%} percentile")
    f = R["factors"]
    print(f"   Momentum ETF vs S&P 500 since {A.PEAK}: {f['mtum_vs_spy']:+.1%}; XLY {f['xly']:+.1%} vs equal weight {f['rspd']:+.1%}")
    print("\n3. SPDR ETF flows from shares outstanding ($bn; z = last week vs past year)")
    fl = pd.DataFrame(R["etf_flows"])
    print(fl[["ticker", "name", "flow_peak_bn", "flow_nov_bn", "flow_week_bn", "z_week"]].round(2)
          .sort_values("flow_peak_bn").to_string(index=False))
    m = R["mmf"]
    print(f"\n4. Money market funds (ICI): ${m['total_tn']:.2f}tn, {m['chg_bn']:+.1f}bn in the week to {m['date'][:10]} "
          f"(z {m['z']:+.1f}); week before {m['prev_chg_bn']:+.1f}bn (z {m['prev_z']:+.1f})")
    n = R["net_liquidity"]
    print(f"   Net liquidity (Fed - TGA - RRP): ${n['now_bn']:,.0f}bn, 4-week change {n['chg_4w_bn']:+,.0f}bn")
    print("\n5. Prices: assets above T-bills")
    for col, label in (("last_week", "last 7 days"), ("november", "November"), ("since_peak", f"since {A.PEAK}")):
        k, tot = R["beat_cash"][col]
        print(f"   {label}: {k} of {tot}")
    print(pd.DataFrame(R["groups_by_start"]).round(3).to_string(index=False))
    print("\n6. Profit-taking or volatility (exploratory checks)")
    print(pd.DataFrame(R["robustness"]).round(2).to_string(index=False))
    print("\n7. Positioning (CFTC)")
    print(pd.DataFrame(R["positioning"]).drop(columns=["net_pct_oi"]).round(2).to_string(index=False))
    print("\nBy hand: BofA fund manager survey (mid-month), ETF.com weekly flows, EPFR via BofA Flow Show.")


def cmd_report(args) -> None:
    from .report import build_pdf

    b = data.load()
    out = collect(b)
    folder = REPORTS / out["last_close"]
    out["external"] = json.loads((folder / "external.json").read_text(encoding="utf-8"))
    (folder / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {build_pdf(b, folder)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="moneyflow")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check", help="print flows, stress, rates and prices")
    s.add_argument("--cached", action="store_true", help="use the saved snapshot instead of downloading")
    s.set_defaults(func=cmd_check)
    sub.add_parser("report", help="write results.json and the PDF").set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
