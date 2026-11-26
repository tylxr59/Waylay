"""Cost math: what each crate fill, writ and receipt costs at current prices.

All money is copper. A row is never dropped for a missing price; it carries a
`missing` list instead so the report can show it and the planner can skip it.
"""

from __future__ import annotations

from typing import Callable

from .tsm import Price

PriceFn = Callable[[Price], "int | None"]

BASES: dict[str, tuple[str, PriceFn]] = {
    "market": ("Market value", lambda p: p.market),
    "buyout": ("Min buyout", lambda p: p.min_buyout or p.market),
    "sale": ("Avg sale price", lambda p: p.avg_sale or p.market),
    "historical": ("Historical", lambda p: p.historical or p.market),
}


def available_bases(prices: dict[int, Price]) -> list[str]:
    """Bases the price file can support (region files have no min buyout, realm files no avg sale)."""
    sample = list(prices.values())[:500]
    out = ["market"]
    if any(p.min_buyout for p in sample):
        out.append("buyout")
    if any(p.avg_sale for p in sample):
        out.append("sale")
    if any(p.historical for p in sample):
        out.append("historical")
    return out


class Pricer:
    def __init__(self, prices: dict[int, Price], basis: str):
        self.prices = prices
        self.fn = BASES[basis][1]

    def unit(self, item_id: int | None) -> int | None:
        if item_id is None or item_id not in self.prices:
            return None
        return self.fn(self.prices[item_id])

    def stat(self, item_id: int | None) -> Price | None:
        return self.prices.get(item_id) if item_id is not None else None


def _deal(p: Price | None, unit: int | None) -> float | None:
    """How far the price sits from TSM's historical price (-0.2 = 20% cheaper than usual)."""
    if not p or not unit or not p.historical:
        return None
    return round(unit / p.historical - 1, 4)


def _min_none(*vals: float | None) -> float | None:
    vals = [v for v in vals if v is not None]
    return min(vals) if vals else None


def crate_options(crates: list[dict], pr: Pricer) -> list[dict]:
    rows = []
    for c in crates:
        crate_price = pr.unit(c["itemId"])
        crate_stat = pr.stat(c["itemId"])
        for opt in c["options"]:
            unit = pr.unit(opt["itemId"])
            stat = pr.stat(opt["itemId"])
            missing = []
            if crate_price is None:
                missing.append(c["name"])
            if unit is None:
                missing.append(opt["name"])
            mat_cost = unit * opt["qty"] if unit is not None else None
            total = mat_cost + crate_price if mat_cost is not None and crate_price is not None else None
            mat_spd = stat.sold_per_day if stat else None
            crate_spd = crate_stat.sold_per_day if crate_stat else None
            rows.append({
                "crateId": c["itemId"],
                "crate": c["name"].replace("Waylaid Crate: ", ""),
                "tier": c["tier"],
                "category": c["category"],
                "quality": c["quality"],
                "reqLevel": c["reqLevel"],
                "favor": c["favor"],
                "note": c.get("note"),
                "itemId": opt["itemId"],
                "item": opt["name"],
                "qty": opt["qty"],
                "unit": unit,
                "crateCost": crate_price,
                "matCost": mat_cost,
                "total": total,
                "perFavor": round(total / c["favor"], 1) if total is not None else None,
                "perFavorOwned": round(mat_cost / c["favor"], 1) if mat_cost is not None else None,
                "deal": _deal(stat, unit),
                "matSoldPerDay": mat_spd,
                "crateSoldPerDay": crate_spd,
                # crates you could realistically fill per day if you only bought what normally sells
                "perDay": _min_none(crate_spd, mat_spd / opt["qty"] if mat_spd is not None else None),
                "missing": missing,
            })
    return rows


def writ_rows(writs: list[dict], pr: Pricer, pouch: dict[str, int]) -> list[dict]:
    rows = []
    for w in writs:
        writ_price = pr.unit(w["itemId"])
        writ_stat = pr.stat(w["itemId"])
        missing = [] if writ_price is not None else [w["name"]]
        items, item_cost, caps = [], 0, []
        for req in w["requires"]:
            unit = pr.unit(req["itemId"])
            stat = pr.stat(req["itemId"])
            if unit is None:
                missing.append(req["name"])
            else:
                item_cost += unit * req["qty"]
            spd = stat.sold_per_day if stat else None
            if spd is not None:
                caps.append(spd / req["qty"])
            items.append({"itemId": req["itemId"], "name": req["name"], "qty": req["qty"], "unit": unit,
                          "soldPerDay": spd, "deal": _deal(stat, unit)})
        coin = pouch.get(w["tier"], 0)
        net = writ_price + item_cost - coin if not missing else None
        writ_spd = writ_stat.sold_per_day if writ_stat else None
        rows.append({
            "itemId": w["itemId"],
            "questId": w.get("questId"),
            "name": w["name"].replace("Craftsman's Writ: ", ""),
            "professions": w["professions"],
            "tier": w["tier"],
            "rep": w["rep"],
            "npc": w.get("npc"),
            "zone": w.get("zone"),
            "coords": w.get("coords"),
            "npcId": w.get("npcId"),
            "npcType": w.get("npcType", "npc"),
            "verified": w.get("requiresSource") == "wowhead-quest",
            "writPrice": writ_price,
            "writSoldPerDay": writ_spd,
            "items": items,
            "itemCost": item_cost if not any(i["unit"] is None for i in items) else None,
            "coin": coin,
            "net": net,
            "perRep": round(net / w["rep"], 1) if net is not None else None,
            "perDay": _min_none(writ_spd, *caps),
            "missing": missing,
        })
    return rows


def summarize(options: list[dict], writs: list[dict], crates: list[dict], pr: Pricer, faction: dict) -> dict:
    priced = [o for o in options if o["perFavor"] is not None]
    best = min(priced, key=lambda o: o["perFavor"]) if priced else None
    crate_prices = [(pr.unit(c["itemId"]), c) for c in crates]
    crate_prices = [(p, c) for p, c in crate_prices if p is not None]
    cheapest = min(crate_prices, key=lambda t: t[0]) if crate_prices else None
    receipt = faction["receipt"]
    receipt_cost = None
    if best and cheapest:
        receipt_cost = receipt["favor"] * best["perFavor"] + cheapest[0]
    best_writ = {}
    for tier in ("Journeyman", "Expert", "Artisan"):
        tw = [w for w in writs if w["tier"] == tier and w["perRep"] is not None]
        if tw:
            b = min(tw, key=lambda w: w["perRep"])
            best_writ[tier] = {"name": b["name"], "perRep": b["perRep"], "net": b["net"], "verified": b["verified"]}
    return {
        "bestFavor": {k: best[k] for k in ("crate", "item", "qty", "total", "perFavor", "favor")} if best else None,
        "cheapestCrate": {"itemId": cheapest[1]["itemId"], "name": cheapest[1]["name"], "price": cheapest[0],
                          "soldPerDay": (pr.stat(cheapest[1]["itemId"]) or Price()).sold_per_day} if cheapest else None,
        "receipt": {"cost": round(receipt_cost, 1), "perRep": round(receipt_cost / receipt["rep"], 1)} if receipt_cost else None,
        "bestWrit": best_writ,
    }


def analyze(data: dict, prices: dict[int, Price], basis: str) -> dict:
    pr = Pricer(prices, basis)
    options = crate_options(data["crates"], pr)
    writs = writ_rows(data["writs"], pr, data["faction"]["coinPouchCopper"])
    crates = [{"itemId": c["itemId"], "name": c["name"], "price": pr.unit(c["itemId"]),
               "soldPerDay": (pr.stat(c["itemId"]) or Price()).sold_per_day} for c in data["crates"]]
    return {
        "crateOptions": options,
        "writs": writs,
        "crates": crates,
        "summary": summarize(options, writs, data["crates"], pr, data["faction"]),
    }


def tracked_item_ids(data: dict) -> set[int]:
    ids: set[int] = set()
    for c in data["crates"]:
        ids.add(c["itemId"])
        ids.update(o["itemId"] for o in c["options"] if o["itemId"])
    for w in data["writs"]:
        ids.add(w["itemId"])
        ids.update(r["itemId"] for r in w["requires"] if r["itemId"])
    return ids
