"""Scrape FII/DII activity. Sources tried in order: NSE -> Groww -> Moneycontrol.

A source only "succeeds" if it parses into a payload that both validates AND
carries complete FII+DII equity data — otherwise fall through to the next.
This prevents committing all-zero rows (header-row/mismatch parses) as if the
scrape worked.

Ported from scripts/scrape.mjs. Groww added because NSE (Akamai bot-wall) and
Moneycontrol (JS-rendered) are unreachable from CI; Groww ships the data
server-rendered inside <script id="__NEXT_DATA__">.
"""

from __future__ import annotations

import json

import httpx
from selectolax.parser import HTMLParser

from .schema import build_payload, parse_groww, parse_moneycontrol_row, parse_nse, zero_block
from .util import fetch_text, log

NSE_WARM = "https://www.nseindia.com/"
NSE_API = "https://www.nseindia.com/api/fiidii"
GROWW_URL = "https://groww.in/fii-dii-data"
MC_URL = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"


def try_nse(today: str) -> dict:
    """NSE official API (cash segment only). Needs a warmup cookie."""
    with httpx.Client(follow_redirects=True, timeout=25.0) as client:
        client.get(NSE_WARM, headers={"User-Agent": _ua(), "Accept": "text/html"})
        r = client.get(
            NSE_API,
            headers={"User-Agent": _ua(), "Accept": "application/json", "Referer": NSE_WARM},
        )
        r.raise_for_status()
        arr = r.json()
    return build_payload(date=today, source="nse", equity=parse_nse(arr), derivative=zero_block())


def try_groww(today: str) -> dict:
    """Groww server-rendered FII/DII cash data (newest row = today's session)."""
    html = fetch_text(GROWW_URL)
    node = HTMLParser(html).css_first("#__NEXT_DATA__")
    if node is None:
        raise ValueError("groww: __NEXT_DATA__ script not found")
    records = parse_groww(json.loads(node.text()))
    latest = records[0]
    return build_payload(date=latest["date"], source="groww", equity=latest["equity"], derivative=zero_block())


def try_moneycontrol(today: str) -> dict:
    """Moneycontrol FII/DII table (first data row)."""
    html = fetch_text(MC_URL)
    tree = HTMLParser(html)
    rows = tree.css("table tr")
    if len(rows) < 2:
        raise ValueError("moneycontrol: no data row")
    cells = [c.text().strip() for c in rows[1].css("td")]
    return build_payload(date=today, source="moneycontrol", equity=parse_moneycontrol_row(cells), derivative=zero_block())


def _ua() -> str:
    from .util import _UA

    return _UA
