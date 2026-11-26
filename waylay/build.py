"""Glue: load data, get prices, snapshot, analyze, render."""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.error
from dataclasses import dataclass, replace
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
          history_dir: Path, snapshot: bool = True, parsed: tuple | None = None,
          label: str | None = None, nav: dict | None = None, extra_meta: dict | None = None) -> dict:
    data = load_data(data_dir)
    if parsed is None:
        parsed = tsm.parse(csv_path.read_text(encoding="utf-8") if csv_path else tsm.fetch(src))
    prices, names, updated = parsed
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
            "source": {"game": src.game, "region": src.region, "realm": src.realm, "label": label or src.label, "url": src.url},
            "nav": nav,
            **(extra_meta or {}),
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


# ---------- every region / ruleset / faction in data/sources.json ----------

@dataclass(frozen=True)
class Site:
    id: str
    source: tsm.Source
    region_name: str
    ruleset: str | None = None       # slug; None = region-wide (all rulesets, both factions)
    ruleset_name: str | None = None
    faction: str | None = None       # alliance / horde, set for ruleset pages

    @property
    def label(self) -> str:
        if not self.ruleset:
            return f"{self.region_name} · all rulesets"
        return f"{self.region_name} · {self.ruleset_name} · {(self.faction or '').title()}"


def load_sites(path: Path) -> tuple[list[Site], str]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    game, names = cfg.get("game", "forever"), cfg.get("rulesetNames", {})
    factions = cfg.get("factions", ["alliance", "horde"])
    sites = []
    for r in cfg["regions"]:
        rname = r.get("name", r["id"].upper())
        sites.append(Site(r["id"], tsm.Source(game, r["id"]), rname))
        for rs in r.get("rulesets", []):
            for f in factions:
                sites.append(Site(f"{r['id']}-{rs}-{f}", tsm.Source(game, r["id"], f"{rs}-{f}"), rname,
                                  rs, names.get(rs, rs), f))
    return sites, cfg.get("default", sites[0].id)


def with_region_volume(prices: dict[int, tsm.Price], region: dict[int, tsm.Price]) -> dict[int, tsm.Price]:
    """Ruleset files have no sales stats; borrow the region's sold/day so the
    planner's volume caps still work (they'll be generous for one auction house)."""
    out = {}
    for i, p in prices.items():
        r = region.get(i)
        out[i] = replace(p, sold_per_day=r.sold_per_day, sale_rate=r.sale_rate) if r and p.sold_per_day is None else p
    return out


def build_all(sources_path: Path, *, out_dir: Path, data_dir: Path, history_dir: Path,
              snapshot: bool = True, fetch=None) -> dict[str, dict]:
    """Build one page per source. The default source is site/index.html, the
    rest site/<id>/index.html. A source that fails to download or is empty is
    skipped (and left out of the menus), unless it is the default."""
    fetch = fetch or tsm.fetch
    sites, default = load_sites(sources_path)
    parsed = {}
    for s in sites:
        try:
            got = tsm.parse(fetch(s.source))
            if not got[0]:
                raise ValueError("no items in file")
            parsed[s.id] = got
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            if s.id == default:
                raise
            print(f"warning: skipped {s.label} ({s.source.url}): {e}", file=sys.stderr)
    ok = [s for s in sites if s.id in parsed]
    path = {s.id: "index.html" if s.id == default else f"{s.id}/index.html" for s in ok}
    menu = [{"id": s.id, "region": s.source.region, "regionName": s.region_name, "ruleset": s.ruleset,
             "rulesetName": s.ruleset_name, "faction": s.faction, "label": s.label, "path": path[s.id]} for s in ok]
    reports = {}
    for s in ok:
        prices, names, updated = parsed[s.id]
        region_wide = parsed.get(s.source.region)
        volume_from = None
        if s.ruleset and region_wide:
            prices, volume_from = with_region_volume(prices, region_wide[0]), "region"
        dest = out_dir if s.id == default else out_dir / s.id
        nav = {"current": s.id, "root": "" if s.id == default else "../", "sources": menu}
        reports[s.id] = build(s.source, csv_path=None, parsed=(prices, names, updated), out_dir=dest,
                              data_dir=data_dir, history_dir=history_dir, snapshot=snapshot, label=s.label,
                              nav=nav, extra_meta={"faction": s.faction, "volumeFrom": volume_from})
    return reports
