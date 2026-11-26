"""TradeSkillMaster public pricing data (https://tradeskillmaster.com/public-data).

The files are static CSVs with prices in copper. TSM asks that each file is
downloaded at most once per update and that the data is credited wherever it
is shown, so the report links back to TSM and the GitHub Action runs once a day.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass

BASE_URL = "https://public-data.tradeskillmaster.com"
USER_AGENT = "waylay-report/1.0 (+https://github.com/tylxr59/Waylay)"


@dataclass(frozen=True)
class Source:
    game: str = "forever"
    region: str = "us"
    realm: str | None = None

    @property
    def url(self) -> str:
        if self.realm:
            return f"{BASE_URL}/{self.game}/{self.region}/realm/{self.realm}/items.csv"
        return f"{BASE_URL}/{self.game}/{self.region}/region/items.csv"

    @property
    def label(self) -> str:
        where = f"realm {self.realm}" if self.realm else "region-wide"
        return f"{self.game} {self.region.upper()} ({where})"


@dataclass(frozen=True)
class Price:
    """One item's TSM stats, all prices in copper. Missing columns are None."""

    market: int | None = None
    historical: int | None = None
    avg_sale: int | None = None
    min_buyout: int | None = None
    recent: int | None = None
    sold_per_day: float | None = None
    sale_rate: float | None = None


def fetch(source: Source, timeout: float = 60) -> str:
    req = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _int(v: str | None) -> int | None:
    if v is None or v == "":
        return None
    n = int(float(v))
    return n if n > 0 else None


def _float(v: str | None) -> float | None:
    if v is None or v == "":
        return None
    return float(v)


def parse(text: str) -> tuple[dict[int, Price], dict[int, str], str | None]:
    """Return (prices by item id, names by item id, upstream scan time)."""
    prices: dict[int, Price] = {}
    names: dict[int, str] = {}
    updated = None
    for row in csv.DictReader(io.StringIO(text)):
        try:
            item_id = int(row["itemId"])
        except (KeyError, ValueError):
            continue
        prices[item_id] = Price(
            market=_int(row.get("marketValue")),
            historical=_int(row.get("historical")),
            avg_sale=_int(row.get("avgSalePrice")),
            min_buyout=_int(row.get("minBuyout")),
            recent=_int(row.get("recent")),
            sold_per_day=_float(row.get("soldPerDay")),
            sale_rate=_float(row.get("saleRate")),
        )
        if row.get("name"):
            names[item_id] = row["name"]
        updated = updated or row.get("updatedAt")
    return prices, names, updated
