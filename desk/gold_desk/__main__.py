"""Command line: python -m gold_desk {forecast,report,backfill,score} (run from the desk/ folder).

The weekly loop is two steps with a human or agent in between:

    python -m gold_desk forecast            # fetch, refit, log forecast, score, write summary.json
    (write reports/<origin>/news.json)      # news, reads and watch list for the week
    python -m gold_desk report              # render reports/<origin>/gold_desk_<origin>.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .rolls import load_rolls
from . import data, store
from .backtest import coverage, score
from .model import N_PATHS, make_forecast
from .summary import build

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _weekly_origins(gold: pd.Series, start: str, end: str | None) -> list[pd.Timestamp]:
    """The last trading day of every week."""
    s = gold.loc[start:end]
    return list(s.groupby(s.index.to_period("W-FRI")).apply(lambda g: g.index[-1]))


def cmd_forecast(args) -> None:
    prices = data.load(refresh=not args.cached)
    gold = data.gold(prices, args.asof)
    fc, _ = make_forecast(gold, source="live")
    store.upsert_live(fc.to_record())
    records = store.read_records()
    scores = score(records, gold, load_rolls())
    origin = f"{fc.origin:%Y-%m-%d}"
    out = REPORTS / origin
    out.mkdir(parents=True, exist_ok=True)
    summary = build(prices, fc, records, scores)
    tested = out / "window_check.json"          # written by `window-check` for this origin, if run
    if tested.exists():
        summary["window_check"] = json.loads(tested.read_text(encoding="utf-8"))
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"origin {origin}  spot {fc.spot:,.1f}  vol {fc.fit.vol_next:.1%}  records {len(records)}")
    print(f"wrote {out / 'summary.json'}")


def cmd_report(args) -> None:
    from .report import build_pdf

    records = store.read_records()
    origin = args.origin or [r for r in records if r["source"] == "live"][-1]["origin"]
    pdf = build_pdf(origin, REPORTS / origin, data.load(), records)
    print(f"wrote {pdf}")


def cmd_backfill(args) -> None:
    prices = data.load(refresh=not args.cached)
    gold = data.gold(prices)
    live = {r["origin"] for r in store.read_records() if r["source"] == "live"}
    origins = [o for o in _weekly_origins(gold, args.start, args.end) if f"{o:%Y-%m-%d}" not in live]
    records = []
    for i, origin in enumerate(origins, 1):
        fc, _ = make_forecast(gold.loc[:origin], source="backfill", n_paths=args.paths)
        records.append(fc.to_record())
        if i % 50 == 0 or i == len(origins):
            print(f"{i}/{len(origins)}  {origin:%Y-%m-%d}  vol {fc.fit.vol_next:.1%}", flush=True)
    store.write_backfill(records)


def cmd_window_check(args) -> None:
    """Expanding sample vs each rolling window on every weekly origin since `--start`."""
    from .backtest import WINDOW_CANDIDATES, window_check, window_qualifies

    prices = data.load(refresh=not args.cached)
    gold = data.gold(prices, args.end)
    origins = _weekly_origins(gold, args.start, args.end)
    returns_before = {o: gold.index.get_loc(o) for o in origins}   # returns available up to o
    base = [make_forecast(gold.loc[:o], source="backfill", n_paths=args.paths)[0].to_record()
            for o in origins]
    rows = []
    for name, window in WINDOW_CANDIDATES.items():
        rolling = [make_forecast(gold.loc[:o], source="backfill", n_paths=args.paths, window=window)[0].to_record()
                   for o in origins if returns_before[o] >= window]
        check = window_check(base, rolling, gold).assign(window=name)
        check["qualifies"] = window_qualifies(check)
        rows.append(check)
    out = pd.concat(rows, ignore_index=True)
    with pd.option_context("display.width", 160, "display.float_format", "{:.4f}".format):
        print(out.to_string(index=False))
    target = Path(args.out) if args.out else REPORTS / f"{gold.index[-1]:%Y-%m-%d}" / "window_check.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out.to_json(orient="records", indent=1, date_format="iso"), encoding="utf-8")
    print(f"wrote {target}")


def cmd_iv_check(args) -> None:
    """GVZ implied volatility vs plain GARCH, scored on every stored weekly forecast."""
    from .backtest import IV_CANDIDATES, iv_check, iv_qualifies

    prices = data.load(refresh=not args.cached)
    gold = data.gold(prices)
    records = store.read_records()
    out = iv_check(records, gold, data.gvz(refresh=not args.cached))
    out["qualifies"] = out["candidate"].map({c: iv_qualifies(out, c) for c in IV_CANDIDATES})
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(out.to_string(index=False))
    last = max(r["origin"] for r in records if r["source"] == "live")
    target = Path(args.out) if args.out else REPORTS / last / "iv_check.json"
    target.write_text(out.to_json(orient="records", indent=1, date_format="iso"), encoding="utf-8")
    print(f"wrote {target}")


def cmd_score(args) -> None:
    prices = data.load(refresh=False)
    records = store.read_records()
    scores = score(records, data.gold(prices), load_rolls())
    with pd.option_context("display.width", 120, "display.float_format", "{:.3f}".format):
        print(coverage(scores, scores["origin"].max()).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="gold_desk")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("forecast", help="refit on the latest close, log the forecast, write summary.json")
    p.add_argument("--asof", help="use closes up to this date (YYYY-MM-DD)")
    p.add_argument("--cached", action="store_true", help="use cached prices instead of downloading")
    p.set_defaults(func=cmd_forecast)
    p = sub.add_parser("report", help="render the PDF for an origin (default: latest live forecast)")
    p.add_argument("--origin")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("backfill", help="reconstruct weekly forecasts for past Fridays")
    p.add_argument("--start", default="2006-01-01")
    p.add_argument("--end")
    p.add_argument("--paths", type=int, default=N_PATHS)
    p.add_argument("--cached", action="store_true")
    p.set_defaults(func=cmd_backfill)
    p = sub.add_parser("window-check", help="test rolling estimation windows against the expanding sample")
    p.add_argument("--start", default="2006-01-01")
    p.add_argument("--end")
    p.add_argument("--paths", type=int, default=N_PATHS)
    p.add_argument("--cached", action="store_true")
    p.add_argument("--out", help="JSON output (default: reports/<last close>/window_check.json)")
    p.set_defaults(func=cmd_window_check)
    p = sub.add_parser("iv-check", help="test GVZ implied volatility against the plain GARCH forecasts")
    p.add_argument("--cached", action="store_true")
    p.add_argument("--out", help="JSON output (default: reports/<last live origin>/iv_check.json)")
    p.set_defaults(func=cmd_iv_check)
    p = sub.add_parser("score", help="print the coverage table")
    p.set_defaults(func=cmd_score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
