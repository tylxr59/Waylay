<p align="center"><img src="waylay/logo.svg" alt="" width="96" height="96"></p>

<h1 align="center">Waylay</h1>

<p align="center">
  The cheapest way to earn <b>Merchant's Favor</b> and <b>Azeroth Commerce Authority / Durotar Supply and Logistics</b> reputation in WoW Forever, priced daily from TradeSkillMaster data.
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-97ca00"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> ·
  <a href="#-quick-start">Quick start</a> ·
  <a href="#-usage">Usage</a> ·
  <a href="#-correcting-game-data">Correcting game data</a>
</p>

---

The Commerce Authority grind has three moving parts. **Waylaid Crates** pay Favor and accept any one of several materials. **Craftsman's Writs** give rep but can only be done once a day each. From Friendly, **Forged Delivery Receipts** turn Favor and an empty crate into rep. Which mix is cheapest depends on today's auction house. Waylay prices every crate fill, writ and receipt from TSM's public data and builds a single HTML page: sortable tables, charts, and a planner that takes you from your current standing to a target standing for the least gold.

> [!NOTE]
> Game data was checked against Wowhead for WoW Forever 1.60.1: every writ's quest objective, all 30 crate tooltips, and the receipt and coin pouch numbers. Nine writs still have no known hand-in location. Elite crates aren't covered.

## 🎯 Features

| Feature | What it does |
| --- | --- |
| 📦 **Favor table** | Every crate × material option, cost per Favor, "vs usual" price, and fills/day the market can support. |
| 📜 **Writ table** | All 150 writs: writ + item − coin pouch, cost per 1,000 rep, hand-in NPC/zone. Filter by tier, profession, zone. |
| 🧭 **Rep planner** | Current standing → target, Legacy bonus, extra Favor to spend. Mixes writs and receipts by price and returns a shopping list. |
| 📉 **Volume-aware** | Caps purchases at TSM's sold-per-day, so the plan doesn't assume 900 Gold Power Cores at today's price. |
| 🔗 **Wowhead links** | Every crate, material, writ, quest and known hand-in NPC links to Wowhead, with its tooltip on hover. |
| 🕰️ **History** | Saves a daily price snapshot to `history/` and charts cheapest Favor and rep cost over time. |

## 📋 Requirements

- Python 3.11+ (standard library only, no packages to install).
- Internet access to `public-data.tradeskillmaster.com`.

## 🚀 Quick start

```sh
python -m waylay build          # fetch US region prices, write site/index.html
xdg-open site/index.html         # or open it in any browser
```

Quick terminal answer, no HTML:

```sh
python -m waylay summary -n 15
```

## 🧭 Usage

| Option | Meaning |
| --- | --- |
| `--all` | Build every region, ruleset and faction in [`data/sources.json`](data/sources.json), one page each. This is what the daily Action runs. |
| `--region us` | TSM region slug (`us`, `eu`, `kr`, `tw`). |
| `--realm <slug>` | One realm's prices instead of the region average. The slug is the last part of the realm's URL on tradeskillmaster.com. |
| `--csv items.csv` | Use a downloaded TSM `items.csv` instead of fetching. |
| `--no-snapshot` | Don't write today's prices to `history/`. |
| `summary --basis sale` | Price basis: `market`, `sale` (avg sale price, region data), `buyout` (min buyout, realm data), `historical`. |

### Daily page on GitHub Pages

[`.github/workflows/report.yml`](.github/workflows/report.yml) runs every day at 10:17 UTC. It runs the tests, builds the report, commits the day's snapshot to `history/`, and deploys `site/` to Pages. To turn it on:

1. **Settings → Pages → Source: GitHub Actions.**
2. **Actions → Daily report → Run workflow** for the first build.

US (all rulesets) is the main page. Every region also gets a page per ruleset and faction, since Forever auction houses are split that way: Normal, PvP, RP and RP-PvP for US and EU, Normal and PvP for KR and TW. Pick them with the Region, Ruleset and Alliance/Horde controls at the top; the main page remembers your last pick. [`data/sources.json`](data/sources.json) lists what gets built. TSM only publishes sold/day region-wide, so ruleset pages borrow the region's numbers for the planner's volume caps.

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
| `HTTP Error 404` with `--realm` | The slug is wrong. Copy it from the realm's URL on tradeskillmaster.com. |
| A row shows `–` | TSM has no price for that item (nothing listed or sold). It's left out of the planner. |
| Planner warns about sales volume | You asked for more than normally sells in that many days. Raise **Days** or untick **Stay within normal sales volume**. |

## 👋 Development

```sh
python -m unittest discover -s tests
```

## 🤝 Acknowledgements

- Pricing data from [TradeSkillMaster](https://tradeskillmaster.com) public data. Waylay is not affiliated with or endorsed by TSM.
- Game data from [Wowhead](https://www.wowhead.com/forever)'s WoW Forever guides and database, [Method.gg](https://www.method.gg/wow-forever) guides, and players reporting in guide comments.

## 📃 License

Waylay is available under the [MIT License](LICENSE).
