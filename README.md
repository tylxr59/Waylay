<p align="center"><img src="waylay/logo.svg" alt="" width="96" height="96"></p>

<h1 align="center">Waylay</h1>

<p align="center">
  The cheapest way to earn <b>Merchant's Favor</b> and <b>Azeroth Commerce Authority / Durotar Supply and Logistics</b> reputation in WoW Forever, priced daily from TradeSkillMaster data.
</p>

<p align="center">
  <a href="https://tylxr59.github.io/Waylay/"><b>🌐 Open the live report: tylxr59.github.io/Waylay</b></a>
</p>

<p align="center">
  <a href="https://github.com/tylxr59/Waylay/actions/workflows/report.yml"><img alt="Daily report" src="https://github.com/tylxr59/Waylay/actions/workflows/report.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-97ca00"></a>
</p>

<p align="center">
  <a href="https://tylxr59.github.io/Waylay/">Live report</a> ·
  <a href="#-features">Features</a> ·
  <a href="#%EF%B8%8F-how-its-built">How it's built</a> ·
  <a href="#%EF%B8%8F-correcting-game-data">Correcting game data</a>
</p>

---

The Commerce Authority grind has three moving parts. **Waylaid Crates** pay Favor and accept any one of several materials. **Craftsman's Writs** give rep but can only be done once a day each. From Friendly, **Forged Delivery Receipts** turn Favor and an empty crate into rep. Which mix is cheapest depends on today's auction house.

**[tylxr59.github.io/Waylay](https://tylxr59.github.io/Waylay/)** prices every crate fill, writ and receipt from TSM's public data each day: sortable tables, charts, and a planner that takes you from your current standing to a target standing for the least gold. Nothing to install.

> [!NOTE]
> Game data was checked against Wowhead for WoW Forever 1.60.1: every writ's quest objective, all 30 crate tooltips, and the receipt and coin pouch numbers. Nine writs still have no known hand-in location. Elite crates aren't covered.

## 🌐 Live report

Pick your **region**, **ruleset** and **faction** at the top of the page; the main page remembers your choice. Forever auction houses are split by ruleset and faction, so each combination gets its own prices: Normal, PvP, RP and RP-PvP in US and EU, Normal and PvP in KR and TW, plus an "All rulesets" average per region.

## 🎯 Features

| Feature | What it does |
| --- | --- |
| 📦 **Favor table** | Every crate × material option, cost per Favor, "vs usual" price, and fills/day the market can support. |
| 📜 **Writ table** | All 150 writs: writ + item − coin pouch, cost per 1,000 rep, hand-in NPC/zone. Filter by tier, profession, zone. |
| 🧭 **Rep planner** | Current standing → target, Legacy bonus, extra Favor to spend. Mixes writs and receipts by price and returns a shopping list. |
| 📉 **Volume-aware** | Caps purchases at TSM's sold-per-day, so the plan doesn't assume 900 Gold Power Cores at today's price. |
| 🔗 **Wowhead links** | Every crate, material, writ, quest and known hand-in NPC links to Wowhead, with its tooltip on hover. |
| 🕰️ **History** | Saves a daily price snapshot to `history/` and charts cheapest Favor and rep cost over time. |

## ⚙️ How it's built

[`.github/workflows/report.yml`](.github/workflows/report.yml) runs every day at 10:17 UTC. It runs the tests, runs `python -m waylay build --all` to download TSM's price files and write one page per region, ruleset and faction, commits the day's snapshot to `history/`, and deploys the pages to GitHub Pages. The generator is plain Python 3.11+ with no dependencies; [`data/sources.json`](data/sources.json) lists which pages get built. TSM only publishes sold/day region-wide, so ruleset pages borrow the region's numbers for the planner's volume caps.

To build it locally:

```sh
python -m waylay build --all     # every page into site/ (add --no-snapshot to leave history/ alone)
python -m waylay build           # just the US region-wide page
python -m waylay summary -n 15   # quick terminal answer, no HTML
python -m unittest discover -s tests
```

`build` also takes `--region`, `--realm <tsm slug>` (e.g. `roleplay-pvp-alliance`) and `--csv items.csv`; `summary` takes `--basis market|sale|buyout|historical`.

## ✏️ Correcting game data

All game knowledge lives in JSON files under `data/`. Fix a number there and the next build picks it up.

| File | Holds |
| --- | --- |
| [`data/crates.json`](data/crates.json) | 30 crates: tier, Favor paid, fill options (item id + qty). |
| [`data/writs.json`](data/writs.json) | 150 writs: tier, rep, hand-in NPC/zone, required item + qty. Set `"requiresSource": "wowhead-quest"` once a requirement is confirmed. |
| [`data/sources.json`](data/sources.json) | Regions and rulesets to build pages for. |
| [`data/faction.json`](data/faction.json) | Standing sizes, receipt rules, first-crate bonus, Legacy bonus, coin pouch averages, Favor rewards. |

## 🩺 Troubleshooting

| Symptom | Fix |
| --- | --- |
| A row shows `–` | TSM has no price for that item (nothing listed or sold). It's left out of the planner. |
| Planner warns about sales volume | You asked for more than normally sells in that many days. Raise **Days** or untick **Stay within normal sales volume**. |

## 🤝 Acknowledgements

- Pricing data from [TradeSkillMaster](https://tradeskillmaster.com) public data. Waylay is not affiliated with or endorsed by TSM.
- Game data from [Wowhead](https://www.wowhead.com/forever)'s WoW Forever guides and database, [Method.gg](https://www.method.gg/wow-forever) guides, and players reporting in guide comments.

## 📃 License

Waylay is available under the [MIT License](LICENSE).
