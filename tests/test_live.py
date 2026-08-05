"""Live-endpoint integration tests — hit real public URLs + upstream sources.

Network-dependent, gated behind LIVE=1 so the default run stays offline.
  LIVE=1 python -m pytest tests/test_live.py
Ported from scripts/live.test.mjs; adds the Groww upstream.
"""

import json
import os

import httpx
import pytest

from fii_dii.schema import validate_payload

LIVE = os.environ.get("LIVE") == "1"
pytestmark = pytest.mark.skipif(not LIVE, reason="set LIVE=1 to run live-endpoint tests")

CANONICAL = "https://chirag127.github.io/fii-dii-activity-api/data"
RAW = "https://raw.githubusercontent.com/chirag127/fii-dii-activity-api/main/data"
JSDELIVR = "https://cdn.jsdelivr.net/gh/chirag127/fii-dii-activity-api@main/data"
STATICALLY = "https://cdn.statically.io/gh/chirag127/fii-dii-activity-api/main/data"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _get_json(url):
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=25, follow_redirects=True)
    return r, (r.json() if r.status_code == 200 else None)


@pytest.mark.parametrize(
    "label,base",
    [
        ("github-pages", CANONICAL),
        ("raw", RAW),
        ("jsdelivr", JSDELIVR),
        ("statically", STATICALLY),
    ],
)
def test_endpoint_latest_json_valid(label, base):
    r, body = _get_json(f"{base}/latest.json")
    assert r.status_code == 200, f"{base}/latest.json returned {r.status_code}"
    ok, errors = validate_payload(body)
    assert ok, f"{label} latest.json invalid: {'; '.join(errors)}"


def test_specific_dated_file_valid():
    _, latest = _get_json(f"{CANONICAL}/latest.json")
    r, body = _get_json(f"{RAW}/{latest['date']}.json")
    assert r.status_code == 200
    assert validate_payload(body)[0]
    assert body["date"] == latest["date"]


def test_upstream_groww_reachable():
    from selectolax.parser import HTMLParser

    r = httpx.get("https://groww.in/fii-dii-data", headers={"User-Agent": UA}, timeout=25, follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f"Groww upstream unreachable ({r.status_code})")
    node = HTMLParser(r.text).css_first("#__NEXT_DATA__")
    assert node is not None
    data = json.loads(node.text())
    assert data["props"]["pageProps"]["initialData"]
