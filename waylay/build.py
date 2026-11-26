"""Glue: load data, get prices, snapshot, analyze, render."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import analysis, history, tsm

ROOT = Path(__file__).resolve().parent.parent
HISTORY_DAYS = 120


def load_data(data_dir: Path) -> dict:
    def read(name: str) -> dict:
        return json.loads((data_dir / name).read_text(encoding="utf-8"))

    return {
        "crates": read("crates.json")["crates"],
        "writs": read("writs.json")["writs"],
        "faction": read("faction.json"),
    }


def source_key(src: tsm.Source) -> str:
    return f"{src.game}-{src.region}-{src.realm or 'region'}"


def history_series(data: dict, days: dict[str, dict], tracked: set[int]) -> dict:
    dates = list(days)[-HISTORY_DAYS:]
    out = {"dates": dates, "bestPerFavor": [], "receiptPerRep": [],
           "bestWritPerRep": {t: [] for t in ("Journeyman", "Expert", "Artisan")}, "items": {}}
    for d in dates:
        s = analysis.analyze(data, days[d], "market")["summary"]
        out["bestPerFavor"].append(s["bestFavor"]["perFavor"] if s["bestFavor"] else None)
        out["receiptPerRep"].append(s["receipt"]["perRep"] if s["receipt"] else None)
        for t, series in out["bestWritPerRep"].items():
            series.append(s["bestWrit"][t]["perRep"] if t in s["bestWrit"] else None)
    for item_id in sorted(tracked):
        series = [days[d][item_id].market if item_id in days[d] else None for d in dates]
        if any(v is not None for v in series):
            out["items"][str(item_id)] = series
    return out


def build(src: tsm.Source, *, csv_path: Path | None, out_dir: Path, data_dir: Path,
          history_dir: Path, snapshot: bool = True) -> dict:
    data = load_data(data_dir)
    text = csv_path.read_text(encoding="utf-8") if csv_path else tsm.fetch(src)
    prices, names, updated = tsm.parse(text)
    date = (updated or dt.datetime.now(dt.timezone.utc).isoformat())[:10]
    tracked = analysis.tracked_item_ids(data)

    key = source_key(src)
    if snapshot:
        history.snapshot(history_dir, key, date, prices, tracked)
    days = history.load(history_dir, key)
    if date not in days:  # no snapshot written (or history disabled): still chart today
        days[date] = {i: prices[i] for i in tracked if i in prices}

    bases = analysis.available_bases(prices)
    report = {
        "meta": {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
            "tsmUpdatedAt": updated,
            "source": {"game": src.game, "region": src.region, "realm": src.realm, "label": src.label, "url": src.url},
            "bases": [{"key": b, "label": analysis.BASES[b][0]} for b in bases],
            "unverifiedWrits": sum(1 for w in data["writs"] if w.get("requiresSource") != "wowhead-quest"),
        },
        "faction": data["faction"],
        "bases": {b: analysis.analyze(data, prices, b) for b in bases},
        "items": {
            str(i): {"name": names.get(i), "market": p.market, "historical": p.historical, "avgSale": p.avg_sale,
                     "minBuyout": p.min_buyout, "soldPerDay": p.sold_per_day}
            for i in sorted(tracked) if (p := prices.get(i))
        },
        "history": history_series(data, days, tracked),
    }
    from .render import render

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render(report), encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps(report, separators=(",", ":")), encoding="utf-8")
    return report
