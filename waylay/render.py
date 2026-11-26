"""Inject the report JSON into the single-file HTML template."""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
MARKER = "/*__WAYLAY_DATA__*/null"


def render(report: dict) -> str:
    payload = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
    # keep the JSON from closing the <script> element early
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError("template is missing the data marker")
    return html.replace(MARKER, payload)
