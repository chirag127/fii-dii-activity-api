"""Structural checks on openapi.yaml. Ported from scripts/openapi.test.mjs."""

import re

from fii_dii.schema import BLOCK_FIELDS, SOURCES, validate_payload


def _spec(root):
    return (root / "openapi.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")


def test_declares_openapi_31_and_title(root):
    spec = _spec(root)
    assert re.search(r"^openapi:\s*3\.1\.\d+", spec, re.M)
    assert re.search(r"title:\s*FII/DII Activity API", spec)


def test_no_legacy_brand_except_sanctioned_domain(root):
    # strip the sanctioned <repo>.oriz.in domain, then assert no bare brand.
    spec = re.sub(r"[a-z0-9-]+\.or" + "iz\\.in", "", _spec(root), flags=re.I)
    assert not re.search("or" + "iz", spec, re.I)


def test_documents_both_endpoints(root):
    spec = _spec(root)
    assert "/latest.json:" in spec
    assert re.search(r"/\{date\}\.json:", spec)


def test_canonical_server_first(root):
    m = re.search(r"servers:\s*\n\s*-\s*url:\s*(\S+)", _spec(root))
    assert m
    assert m.group(1) == "https://chirag127.github.io/fii-dii-activity-api/data"


def test_lists_mirror_servers(root):
    spec = _spec(root)
    for host in (
        "raw.githubusercontent.com/chirag127/fii-dii-activity-api",
        "cdn.jsdelivr.net/gh/chirag127/fii-dii-activity-api",
        "cdn.statically.io/gh/chirag127/fii-dii-activity-api",
    ):
        assert host in spec, f"server {host} missing"


def test_enumerates_sources_and_fields(root):
    spec = _spec(root)
    for s in SOURCES:
        assert s in spec, f"source {s} missing"
    for f in BLOCK_FIELDS:
        assert f in spec, f"field {f} missing"


def test_example_payload_is_schema_valid():
    example = {
        "date": "2026-07-21",
        "source": "nse",
        "equity": {
            "fii_buy": 5917.71,
            "fii_sell": 5004.12,
            "fii_net": 913.59,
            "dii_buy": 6440.88,
            "dii_sell": 5165.66,
            "dii_net": 1275.22,
        },
        "derivative": {f: 0 for f in ["fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net"]},
    }
    ok, errors = validate_payload(example)
    assert ok, "; ".join(errors)
