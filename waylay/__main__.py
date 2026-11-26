"""Command line: `python -m waylay build` / `python -m waylay summary`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analysis, tsm
from .build import ROOT, build, build_all, load_data


def money(c: float | None) -> str:
    if c is None:
        return "-"
    c = round(c)
    g, rem = divmod(c, 10000)
    s, cp = divmod(rem, 100)
    if g:
        return f"{g}g {s:02d}s"
    if s:
        return f"{s}s {cp:02d}c"
    return f"{cp}c"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="waylay", description="Cheapest Merchant's Favor and Commerce Authority rep, from TSM prices.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "summary"):
        p = sub.add_parser(name)
        p.add_argument("--game", default="forever", help="TSM game slug (default: forever)")
        p.add_argument("--region", default="us", help="TSM region slug (default: us)")
        p.add_argument("--realm", help="TSM realm slug; omit for region-wide prices")
        p.add_argument("--csv", type=Path, help="Use a downloaded TSM items.csv instead of fetching")
        p.add_argument("--data", type=Path, default=ROOT / "data")
        if name == "build":
            p.add_argument("--out", type=Path, default=ROOT / "site")
            p.add_argument("--history", type=Path, default=ROOT / "history")
            p.add_argument("--no-snapshot", action="store_true", help="Don't write today's prices to history/")
            p.add_argument("--all", action="store_true",
                           help="Build every region/ruleset in data/sources.json (ignores --region/--realm/--csv)")
        else:
            p.add_argument("--basis", default="market", choices=list(analysis.BASES))
            p.add_argument("-n", type=int, default=10, help="Rows per table")
    args = ap.parse_args(argv)
    src = tsm.Source(args.game, args.region, args.realm)

    if args.cmd == "build" and args.all:
        reports = build_all(args.data / "sources.json", out_dir=args.out, data_dir=args.data,
                            history_dir=args.history, snapshot=not args.no_snapshot)
        for r in reports.values():
            s, nav = r["bases"]["market"]["summary"], r["meta"]["nav"]
            here = next(x for x in nav["sources"] if x["id"] == nav["current"])
            best = money(s["bestFavor"]["perFavor"]) if s["bestFavor"] else "-"
            print(f"Wrote {args.out / here['path']} ({here['label']}): cheapest Favor {best}")
        return 0

    if args.cmd == "build":
        report = build(src, csv_path=args.csv, out_dir=args.out, data_dir=args.data,
                       history_dir=args.history, snapshot=not args.no_snapshot)
        s = report["bases"]["market"]["summary"]
        print(f"Wrote {args.out / 'index.html'} ({src.label}, TSM scan {report['meta']['tsmUpdatedAt']})")
        if s["bestFavor"]:
            print(f"  Cheapest Favor: {money(s['bestFavor']['perFavor'])}/Favor ({s['bestFavor']['crate']} with {s['bestFavor']['item']})")
        if s["receipt"]:
            print(f"  Receipt route:  {money(s['receipt']['perRep'] * 1000)} per 1,000 rep")
        return 0

    data = load_data(args.data)
    text = args.csv.read_text(encoding="utf-8") if args.csv else tsm.fetch(src)
    prices, _, updated = tsm.parse(text)
    res = analysis.analyze(data, prices, args.basis)
    print(f"{src.label} - TSM scan {updated} - basis: {analysis.BASES[args.basis][0]}\n")
    print("Cheapest Merchant's Favor (buy crate + materials):")
    opts = sorted((o for o in res["crateOptions"] if o["perFavor"] is not None), key=lambda o: o["perFavor"])
    for o in opts[: args.n]:
        print(f"  {money(o['perFavor']):>10}/Favor  {o['crate']:<26} {o['qty']:>3} x {o['item']:<24} total {money(o['total'])}")
    print("\nCheapest reputation (buy writ + item, minus coin pouch):")
    ws = sorted((w for w in res["writs"] if w["perRep"] is not None), key=lambda w: w["perRep"])
    for w in ws[: args.n]:
        flag = "" if w["verified"] else "  (requirement unverified)"
        print(f"  {money(w['perRep'] * 1000):>10}/1k rep  {w['name']:<30} {w['tier']:<10} net {money(w['net'])}{flag}")
    s = res["summary"]
    if s["receipt"]:
        print(f"\nForged Delivery Receipt route (Friendly+): {money(s['receipt']['perRep'] * 1000)} per 1,000 rep "
              f"(15 Favor + cheapest empty crate: {s['cheapestCrate']['name']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
