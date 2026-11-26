import json
import tempfile
import unittest
from pathlib import Path

from waylay import analysis, history, tsm
from waylay.build import ROOT, build, build_all, load_data, with_region_volume
from waylay.render import render

FACTION = json.loads((ROOT / "data" / "faction.json").read_text(encoding="utf-8"))

CRATES = [{
    "itemId": 1, "name": "Waylaid Crate: Apprentice Ore", "tier": "Apprentice", "category": "Ore",
    "quality": "common", "reqLevel": 10, "favor": 5,
    "options": [{"itemId": 10, "name": "Copper Ore", "qty": 20}, {"itemId": 11, "name": "Tin Ore", "qty": 20}],
}]
WRITS = [{
    "itemId": 2, "name": "Craftsman's Writ: Golden Rod", "professions": ["Blacksmithing"], "tier": "Journeyman",
    "rep": 75, "requires": [{"itemId": 20, "name": "Golden Rod", "qty": 1}], "requiresSource": "wowhead-quest",
}]
CSV = """itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt
1,Waylaid Crate: Apprentice Ore,500,400,450,0.5,10,2026-11-25T08:58:46Z
10,Copper Ore,100,125,90,0.9,300,2026-11-25T08:58:46Z
11,Tin Ore,200,200,0,0.9,40,2026-11-25T08:58:46Z
2,Craftsman's Writ: Golden Rod,10000,10000,9000,0.4,5,2026-11-25T08:58:46Z
20,Golden Rod,3000,3000,2800,0.5,20,2026-11-25T08:58:46Z
"""


class CostMath(unittest.TestCase):
    def setUp(self):
        self.prices, self.names, self.updated = tsm.parse(CSV)
        self.data = {"crates": CRATES, "writs": WRITS, "faction": FACTION}

    def test_parse(self):
        self.assertEqual(self.prices[10].market, 100)
        self.assertIsNone(self.prices[11].avg_sale)  # 0 means no data
        self.assertEqual(self.updated, "2026-11-25T08:58:46Z")
        self.assertEqual(self.names[20], "Golden Rod")

    def test_crate_option_cost_per_favor(self):
        res = analysis.analyze(self.data, self.prices, "market")
        copper = next(o for o in res["crateOptions"] if o["item"] == "Copper Ore")
        self.assertEqual(copper["matCost"], 2000)
        self.assertEqual(copper["total"], 2500)
        self.assertEqual(copper["perFavor"], 500.0)
        self.assertEqual(copper["perFavorOwned"], 400.0)
        self.assertEqual(copper["deal"], -0.2)  # 100 vs historical 125
        self.assertEqual(copper["perDay"], 10)  # crate sells 10/day, ore supports 15
        self.assertEqual(res["summary"]["bestFavor"]["item"], "Copper Ore")

    def test_writ_net_subtracts_coin_pouch(self):
        res = analysis.analyze(self.data, self.prices, "market")
        w = res["writs"][0]
        pouch = FACTION["coinPouchCopper"]["Journeyman"]
        self.assertEqual(w["net"], 10000 + 3000 - pouch)
        self.assertAlmostEqual(w["perRep"], round((13000 - pouch) / 75, 1))
        self.assertEqual(w["perDay"], 5)

    def test_receipt_route(self):
        s = analysis.analyze(self.data, self.prices, "market")["summary"]
        self.assertEqual(s["receipt"]["cost"], 15 * 500 + 500)
        self.assertEqual(s["receipt"]["perRep"], 160.0)

    def test_missing_price_is_flagged_not_dropped(self):
        prices = dict(self.prices)
        del prices[20]
        w = analysis.analyze(self.data, prices, "market")["writs"][0]
        self.assertIsNone(w["net"])
        self.assertIn("Golden Rod", w["missing"])

    def test_bases(self):
        self.assertEqual(analysis.available_bases(self.prices), ["market", "sale", "historical"])
        sale = analysis.analyze(self.data, self.prices, "sale")
        tin = next(o for o in sale["crateOptions"] if o["item"] == "Tin Ore")
        self.assertEqual(tin["unit"], 200)  # no sales -> falls back to market


class Pipeline(unittest.TestCase):
    def test_history_snapshot_is_idempotent(self):
        prices, _, _ = tsm.parse(CSV)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            history.snapshot(root, "k", "2026-11-25", prices, {1, 10})
            history.snapshot(root, "k", "2026-11-25", prices, {1, 10})
            history.snapshot(root, "k", "2026-11-26", prices, {1})
            days = history.load(root, "k")
            self.assertEqual(list(days), ["2026-11-25", "2026-11-26"])
            self.assertEqual(set(days["2026-11-25"]), {1, 10})

    def test_render_escapes_script_close(self):
        html = render({"x": "</script><b>"})
        self.assertNotIn("</script><b>", html)
        self.assertNotIn("__WAYLAY_", html)  # logo + favicon filled in
        self.assertIn('rel="icon" type="image/svg+xml" href="data:image/svg+xml,', html)

    def test_repo_data_is_consistent(self):
        data = load_data(ROOT / "data")
        self.assertEqual(len(data["crates"]), 30)
        self.assertEqual(len(data["writs"]), 150)
        for c in data["crates"]:
            self.assertIn(c["favor"], (5, 10, 15, 20, 30, 40))
            self.assertTrue(c["options"])
        for w in data["writs"]:
            self.assertEqual(w["rep"], FACTION["writRepByTier"][w["tier"]])
            self.assertTrue(all(r["itemId"] for r in w["requires"]), w["name"])

    def test_build_all_sources(self):
        import urllib.error
        realm_csv = ("itemId,name,marketValue,minBuyout,recent,historical,updatedAt\n"
                     "10,Copper Ore,90,95,95,100,2026-11-26T18:00:00Z\n")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "sources.json").write_text(json.dumps({"default": "us", "rulesetNames": {"roleplay-pvp": "RP-PvP"},
                "regions": [{"id": "us", "name": "US", "rulesets": ["roleplay-pvp"]},
                            {"id": "eu", "name": "EU"}, {"id": "kr", "name": "KR", "rulesets": ["roleplay-pvp"]}]}),
                encoding="utf-8")

            def fetch(src):
                if src.region == "kr" and not src.realm:
                    raise urllib.error.HTTPError(src.url, 404, "Not Found", None, None)
                if src.region == "kr":
                    return "itemId,name,marketValue\n"  # empty file
                return realm_csv if src.realm else CSV

            reports = build_all(d / "sources.json", out_dir=d / "site", data_dir=ROOT / "data",
                                history_dir=d / "history", fetch=fetch)
            self.assertEqual(list(reports), ["us", "us-roleplay-pvp-alliance", "us-roleplay-pvp-horde", "eu"])
            self.assertTrue((d / "site" / "index.html").exists())
            self.assertTrue((d / "site" / "us-roleplay-pvp-horde" / "index.html").exists())
            meta = reports["us-roleplay-pvp-alliance"]["meta"]
            self.assertEqual(meta["source"]["label"], "US · RP-PvP · Alliance")
            self.assertEqual((meta["faction"], meta["volumeFrom"], meta["nav"]["root"]), ("alliance", "region", "../"))
            self.assertEqual(meta["nav"]["sources"][0]["path"], "index.html")
            # ruleset price, region sold/day
            merged = with_region_volume(tsm.parse(realm_csv)[0], tsm.parse(CSV)[0])
            self.assertEqual((merged[10].market, merged[10].sold_per_day), (90, 300))
            self.assertTrue((d / "history" / "forever-us-roleplay-pvp-alliance").is_dir())

    def test_build_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "items.csv").write_text(CSV, encoding="utf-8")
            report = build(tsm.Source(), csv_path=d / "items.csv", out_dir=d / "site",
                           data_dir=ROOT / "data", history_dir=d / "history")
            self.assertTrue((d / "site" / "index.html").exists())
            self.assertEqual(report["history"]["dates"], ["2026-11-25"])


if __name__ == "__main__":
    unittest.main()
