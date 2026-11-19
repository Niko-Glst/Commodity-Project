"""Command line (run from copper/):

    python -m dr_copper fetch     # download daily closes into data/prices.csv
    python -m dr_copper test      # run the pre-registered test and the side analyses -> reports/<date>/results.json
    python -m dr_copper report    # render reports/<date>/dr_copper_<date>.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as A
from . import data

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def collect(df: pd.DataFrame) -> dict:
    last = df.index[-1]
    wr = A.weekly_returns(df)
    roll = wr[A.COPPER].rolling(52).corr(wr[A.TARGET])
    prior = roll.iloc[:-26]
    higher = prior[prior >= roll.iloc[-1]]
    eras = {b: A.era_correlations(wr, A.COPPER, b) for b in ("^IXIC", "^NDX", "^SOX", "^GSPC")}
    ai_vs_2010s = {}
    for b, e in eras.items():
        ai, ref = e.iloc[-1], e.loc[e.era == "2010-2019"].iloc[0]
        ai_vs_2010s[b] = dict(zip(("z", "p"), A.fisher_diff(ai["corr"], int(ai["n"]), ref["corr"], int(ref["n"]))))
    snap = {}
    for t in ("HG=F", "^IXIC", "^NDX", "^SOX", "^GSPC", "FCX", "COPX", "GC=F", "DX-Y.NYB"):
        s = df[t].dropna()
        hi = s.loc["2025":]
        snap[t] = {"last": float(s.iloc[-1]), "nov": float(s.iloc[-1] / s.loc[:"2026-10-30"].iloc[-1] - 1),
                   "high": float(hi.max()), "high_date": str(hi.idxmax().date()),
                   "from_high": float(s.iloc[-1] / hi.max() - 1), "day": float(s.iloc[-1] / s.iloc[-2] - 1)}
    cu_high = pd.Timestamp(snap["HG=F"]["high_date"])
    ratio = np.log(df[A.COPPER] / df[A.GOLD])
    w = A.weekly_closes(pd.DataFrame({"ratio": ratio, "tnx": df["^TNX"]}).dropna())
    off = A.copper_off_high(df).dropna()
    return {
        "last_close": str(last.date()),
        "snapshot": snap,
        "dollar_since_copper_high": float(df["DX-Y.NYB"].dropna().iloc[-1] / df["DX-Y.NYB"].loc[:cu_high].iloc[-1] - 1),
        "rolling_corr_now": float(roll.iloc[-1]), "rolling_corr_sox_now": float(wr[A.COPPER].rolling(52).corr(wr["^SOX"]).iloc[-1]),
        "rolling_corr_last_higher": str(higher.index.max().date()) if len(higher) else None,
        "rolling_corr_max": float(roll.max()), "rolling_corr_max_date": str(roll.idxmax().date()),
        "eras": {b: _records(e) for b, e in eras.items()}, "ai_vs_2010s": ai_vs_2010s,
        "preregistered": _records(A.preregistered(df)), "rule": {"p_max": A.P_MAX, "target": A.TARGET,
                                                                  "horizon_weeks": A.HORIZON, "burn_in": A.BURN_IN},
        "secondary": _records(A.secondary(df)),
        "regimes": _records(A.regimes(df)), "regimes_sox": _records(A.regimes(df, target="^SOX")),
        "bear_peaks": _records(A.bear_peaks(df)),
        "copper_off_high": {"median": float(off.median()), "share_7pct": float((off <= -0.07).mean()),
                            "now": float(off.iloc[-1])},
        "ratio_vs_10y": {"level_corr": float(w.ratio.corr(w.tnx)),
                         "chg13_corr": float(w.ratio.diff(13).corr(w.tnx.diff(13))),
                         "level_corr_2023": float(w.loc["2023":].ratio.corr(w.loc["2023":].tnx)),
                         "chg13_corr_2023": float(w.loc["2023":].ratio.diff(13).corr(w.loc["2023":].tnx.diff(13)))},
    }


def cmd_fetch(args) -> None:
    df = data.load(refresh=True)
    print(f"{len(df)} rows, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d} -> {data.PRICES}")


def cmd_test(args) -> None:
    df = data.load()
    out = collect(df)
    target = REPORTS / out["last_close"] / "results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1), encoding="utf-8")
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(pd.DataFrame(out["preregistered"])[["candidate", "n", "r2_os", "cw_p", "r2_early", "r2_late", "qualifies"]]
              .to_string(index=False))
    print(f"wrote {target}")


def cmd_report(args) -> None:
    from .report import build_pdf

    df = data.load()
    date = args.date or f"{df.index[-1]:%Y-%m-%d}"
    print(f"wrote {build_pdf(df, REPORTS / date)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="dr_copper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download daily closes").set_defaults(func=cmd_fetch)
    sub.add_parser("test", help="run the pre-registered test and side analyses").set_defaults(func=cmd_test)
    p = sub.add_parser("report", help="render the PDF")
    p.add_argument("--date", help="report folder (default: last close)")
    p.set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
