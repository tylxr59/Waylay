"""Daily price snapshots of the items Waylay tracks, kept in git as monthly CSVs.

TSM's public files only hold the current scan, so history has to be collected:
each build appends one row per tracked item for that day (re-running the same
day replaces the day's rows).
"""

from __future__ import annotations

import csv
from pathlib import Path

from .tsm import Price

FIELDS = ["date", "itemId", "market", "historical", "avgSale", "minBuyout", "soldPerDay"]


def source_dir(root: Path, key: str) -> Path:
    return root / key


def snapshot(root: Path, key: str, date: str, prices: dict[int, Price], item_ids: set[int]) -> Path:
    folder = source_dir(root, key)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{date[:7]}.csv"
    kept = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            kept = [r for r in csv.DictReader(f) if r["date"] != date]
    new = []
    for item_id in sorted(item_ids):
        p = prices.get(item_id)
        if p is None:
            continue
        new.append({
            "date": date, "itemId": item_id, "market": p.market or "", "historical": p.historical or "",
            "avgSale": p.avg_sale or "", "minBuyout": p.min_buyout or "",
            "soldPerDay": "" if p.sold_per_day is None else p.sold_per_day,
        })
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(kept + new)
    return path


def load(root: Path, key: str) -> dict[str, dict[int, Price]]:
    """All snapshots for a source, oldest first: {date: {item id: Price}}."""
    days: dict[str, dict[int, Price]] = {}
    folder = source_dir(root, key)
    if not folder.exists():
        return days
    for path in sorted(folder.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                days.setdefault(r["date"], {})[int(r["itemId"])] = Price(
                    market=int(r["market"]) if r["market"] else None,
                    historical=int(r["historical"]) if r["historical"] else None,
                    avg_sale=int(r["avgSale"]) if r["avgSale"] else None,
                    min_buyout=int(r["minBuyout"]) if r["minBuyout"] else None,
                    sold_per_day=float(r["soldPerDay"]) if r["soldPerDay"] else None,
                )
    return dict(sorted(days.items()))
