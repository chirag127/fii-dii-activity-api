"""Unit tests for the pure schema/parsing helpers. No network, no fs.

Ported from scripts/lib/schema.test.mjs.
"""

import math

import pytest

from fii_dii.schema import (
    BLOCK_FIELDS,
    SOURCES,
    build_payload,
    has_complete_equity,
    has_data,
    is_zero_block,
    make_block,
    parse_moneycontrol_row,
    parse_nse,
    to_number,
    validate_payload,
    zero_block,
)


def test_zero_block_has_all_six_fields_at_zero():
    b = zero_block()
    assert sorted(b) == sorted(BLOCK_FIELDS)
    assert all(b[f] == 0 for f in BLOCK_FIELDS)


def test_to_number_coerces_numbers_strings_junk_currency():
    assert to_number(42) == 42
    assert to_number("1,234.5") == 1234.5
    assert to_number("₹ 9,999") == 9999
    assert to_number("-") == 0
    assert to_number("") == 0
    assert to_number(None) == 0
    assert to_number("21-Jul-2026") == 0  # a date is NOT a number
    assert to_number(math.nan) == 0
    assert to_number(math.inf) == 0
    assert to_number("-500.25") == -500.25
    assert to_number("(913.59)") == -913.59  # accounting parenthetical = negative
    assert to_number("(1,234)") == -1234


def test_make_block_derives_net_when_absent_honors_explicit():
    derived = make_block(fii={"buy": 100, "sell": 40}, dii={"buy": 10, "sell": 25})
    assert derived["fii_net"] == 60
    assert derived["dii_net"] == -15
    explicit = make_block(fii={"buy": 100, "sell": 40, "net": 999})
    assert explicit["fii_net"] == 999


def test_validate_payload_accepts_canonical():
    p = build_payload(
        date="2026-07-21",
        source="nse",
        equity=make_block(fii={"buy": 100, "sell": 40}, dii={"buy": 10, "sell": 5}),
    )
    ok, errors = validate_payload(p)
    assert ok, "; ".join(errors)


def test_validate_payload_rejects_bad_inputs():
    assert not validate_payload(None)[0]
    assert not validate_payload({})[0]
    assert not validate_payload({"date": "nope", "source": "nse", "equity": zero_block(), "derivative": zero_block()})[0]
    assert not validate_payload({"date": "2026-07-21", "source": "bogus", "equity": zero_block(), "derivative": zero_block()})[0]

    nan = build_payload(date="2026-07-21", source="nse")
    nan["equity"]["fii_buy"] = math.nan
    assert not validate_payload(nan)[0]

    mismatch = build_payload(date="2026-07-21", source="nse")
    mismatch["equity"]["fii_buy"] = 100
    mismatch["equity"]["fii_sell"] = 40
    mismatch["equity"]["fii_net"] = 999  # 100-40 != 999
    assert not validate_payload(mismatch)[0]


def test_sources_precedence_order():
    assert SOURCES == ["nse", "groww", "moneycontrol", "placeholder"]


def test_is_zero_block_and_has_data():
    assert is_zero_block(zero_block()) is True
    assert is_zero_block(make_block(fii={"buy": 1})) is False
    all_zero = build_payload(date="2026-07-21", source="moneycontrol")
    assert has_data(all_zero) is False
    real = build_payload(date="2026-07-21", source="nse", equity=make_block(fii={"buy": 100, "sell": 40}))
    assert has_data(real) is True


def test_has_complete_equity_requires_both_sides():
    both = build_payload(
        date="2026-07-21",
        source="nse",
        equity=make_block(fii={"buy": 100, "sell": 40}, dii={"buy": 50, "sell": 30}),
    )
    assert has_complete_equity(both) is True
    fii_only = build_payload(date="2026-07-21", source="nse", equity=make_block(fii={"buy": 100, "sell": 40}))
    assert has_complete_equity(fii_only) is False
    dii_only = build_payload(date="2026-07-21", source="nse", equity=make_block(dii={"buy": 50, "sell": 30}))
    assert has_complete_equity(dii_only) is False
    assert has_complete_equity(build_payload(date="2026-07-21", source="placeholder")) is False


def test_parse_nse_extracts_fii_and_dii():
    arr = [
        {"category": "DII **", "buyValue": "6440.88", "sellValue": "5165.66", "netValue": "1275.22"},
        {"category": "FII/FPI *", "buyValue": "5917.71", "sellValue": "5004.12", "netValue": "913.59"},
    ]
    b = parse_nse(arr)
    assert b["fii_buy"] == 5917.71
    assert b["fii_sell"] == 5004.12
    assert b["fii_net"] == 913.59
    assert b["dii_buy"] == 6440.88
    assert b["dii_sell"] == 5165.66
    assert b["dii_net"] == 1275.22


def test_parse_nse_row_order_independent():
    fii_first = [
        {"category": "FII/FPI *", "buyValue": "1", "sellValue": "2", "netValue": "-1"},
        {"category": "DII **", "buyValue": "3", "sellValue": "4", "netValue": "-1"},
    ]
    b = parse_nse(fii_first)
    assert b["fii_buy"] == 1
    assert b["dii_buy"] == 3


def test_parse_nse_throws_on_non_array():
    with pytest.raises(ValueError):
        parse_nse(None)
    with pytest.raises(ValueError):
        parse_nse({"category": "FII"})


def test_parse_moneycontrol_row_drops_leading_date():
    cells = ["21-Jul-2026", "5,917.71", "5,004.12", "913.59", "6,440.88", "5,165.66", "1,275.22"]
    b = parse_moneycontrol_row(cells)
    assert b["fii_buy"] == 5917.71
    assert b["fii_sell"] == 5004.12
    assert b["fii_net"] == 913.59
    assert b["dii_buy"] == 6440.88
    assert b["dii_sell"] == 5165.66
    assert b["dii_net"] == 1275.22


def test_parse_moneycontrol_row_tolerates_short_rows():
    b = parse_moneycontrol_row(["21-Jul-2026"])
    assert b["fii_buy"] == 0
    assert has_data({"equity": b, "derivative": zero_block()}) is False
