"""Inject the report JSON into the single-file HTML template."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
LOGO = Path(__file__).with_name("logo.svg")
MARKER = "/*__WAYLAY_DATA__*/null"
ICON_MARKER = "__WAYLAY_ICON__"
LOGO_MARKER = "<!--__WAYLAY_LOGO__-->"


def render(report: dict) -> str:
    payload = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
    # keep the JSON from closing the <script> element early
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError("template is missing the data marker")
    logo = LOGO.read_text(encoding="utf-8").strip()
    icon = "data:image/svg+xml," + urllib.parse.quote(logo, safe=" =:/,'")
    inline = logo.replace('role="img" aria-label="Waylay"', 'aria-hidden="true" class="logo"', 1)
    return html.replace(ICON_MARKER, icon).replace(LOGO_MARKER, inline).replace(MARKER, payload)
