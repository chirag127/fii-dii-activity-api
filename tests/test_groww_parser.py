"""Groww parser test against a captured real fixture (offline, deterministic)."""

import json
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from fii_dii.schema import BLOCK_FIELDS, has_complete_equity, parse_groww, validate_payload
from fii_dii.__main__ import build_payload

FIXTURE = Path(__file__).parent / "fixtures" / "groww.html"


def _records():
    node = HTMLParser(FIXTURE.read_text(encoding="utf-8")).css_first("#__NEXT_DATA__")
    return parse_groww(json.loads(node.text()))


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not captured")
def test_parses_multiple_days():
    recs = _records()
    assert len(recs) >= 5
    for r in recs:
        assert r["date"]
        assert sorted(r["equity"]) == sorted(BLOCK_FIELDS)


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not captured")
def test_latest_record_is_complete_and_valid():
    recs = _records()
    latest = recs[0]
    payload = build_payload(date=latest["date"], source="groww", equity=latest["equity"])
    ok, errors = validate_payload(payload)
    assert ok, "; ".join(errors)
    assert has_complete_equity(payload)


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not captured")
def test_net_consistency():
    for r in _records():
        eq = r["equity"]
        assert abs(eq["fii_net"] - (eq["fii_buy"] - eq["fii_sell"])) < 1.0
        assert abs(eq["dii_net"] - (eq["dii_buy"] - eq["dii_sell"])) < 1.0
