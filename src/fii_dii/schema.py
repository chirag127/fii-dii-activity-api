"""Shared schema + validation for FII/DII activity payloads.

Pure functions, no I/O — safe to unit-test without network or fs.
Ported 1:1 from the original scripts/lib/schema.mjs.
"""

from __future__ import annotations

import re
from typing import Any

# Ordered numeric fields present in every FII/DII block.
BLOCK_FIELDS = ["fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net"]

# Sources a payload may declare, in fallback precedence order.
SOURCES = ["nse", "groww", "moneycontrol", "placeholder"]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PAREN_RE = re.compile(r"^\((.+)\)$")


def zero_block() -> dict[str, float]:
    """A zeroed activity block."""
    return {f: 0.0 for f in BLOCK_FIELDS}


def to_number(value: Any) -> float:
    """Coerce a scraped value to a finite number.

    Strips commas/whitespace/currency symbols; returns 0.0 for junk.
    Accounting notation '(913.59)' -> -913.59.
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if _finite(value) else 0.0
    if value is None:
        return 0.0
    cleaned = re.sub(r"[,\s₹]", "", str(value)).strip()
    if cleaned in ("", "-"):
        return 0.0
    m = _PAREN_RE.match(cleaned)
    if m:
        cleaned = "-" + m.group(1)
    try:
        n = float(cleaned)
    except ValueError:
        return 0.0
    return n if _finite(n) else 0.0


def _finite(n: float) -> bool:
    return n == n and n not in (float("inf"), float("-inf"))


def _round2(n: float) -> float:
    return round(n + 0.0, 2)


def make_block(fii: dict | None = None, dii: dict | None = None) -> dict[str, float]:
    """Build a block from raw buy/sell/net triples for FII and DII.

    Prefers explicit net when provided, else derives buy - sell.
    """
    fii = fii or {}
    dii = dii or {}
    fii_buy = to_number(fii.get("buy"))
    fii_sell = to_number(fii.get("sell"))
    dii_buy = to_number(dii.get("buy"))
    dii_sell = to_number(dii.get("sell"))
    return {
        "fii_buy": fii_buy,
        "fii_sell": fii_sell,
        "fii_net": to_number(fii["net"]) if fii.get("net") is not None else _round2(fii_buy - fii_sell),
        "dii_buy": dii_buy,
        "dii_sell": dii_sell,
        "dii_net": to_number(dii["net"]) if dii.get("net") is not None else _round2(dii_buy - dii_sell),
    }


def build_payload(date: str, source: str, equity: dict | None = None, derivative: dict | None = None) -> dict:
    """Assemble a canonical payload, filling any missing block with zeros."""
    return {
        "date": date,
        "source": source,
        "equity": equity if equity is not None else zero_block(),
        "derivative": derivative if derivative is not None else zero_block(),
    }


def validate_payload(payload: Any) -> tuple[bool, list[str]]:
    """Validate a full payload. Returns (ok, errors)."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["payload is not an object"]

    date = payload.get("date")
    if not (isinstance(date, str) and _DATE_RE.match(date)):
        errors.append(f"invalid date: {date!r}")

    if payload.get("source") not in SOURCES:
        errors.append(f"invalid source: {payload.get('source')!r}")

    for key in ("equity", "derivative"):
        block = payload.get(key)
        if not isinstance(block, dict):
            errors.append(f"missing block: {key}")
            continue
        for field in BLOCK_FIELDS:
            v = block.get(field)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not _finite(float(v)):
                errors.append(f"{key}.{field} is not a finite number: {v!r}")
        # Cross-check net consistency (tolerate small rounding drift).
        for side in ("fii", "dii"):
            b, s, n = block.get(f"{side}_buy"), block.get(f"{side}_sell"), block.get(f"{side}_net")
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (b, s, n)):
                if abs(b - s - n) > 1:
                    errors.append(f"{key}.{side}_net inconsistent with buy-sell")

    return (len(errors) == 0), errors


def is_zero_block(block: Any) -> bool:
    """True when every field of a block is exactly zero (suspected silent failure)."""
    if not isinstance(block, dict):
        return True
    return all(to_number(block.get(f)) == 0 for f in BLOCK_FIELDS)


def has_data(payload: Any) -> bool:
    """A payload carries real data if at least one block has a non-zero field."""
    if not isinstance(payload, dict):
        return False
    return not is_zero_block(payload.get("equity")) or not is_zero_block(payload.get("derivative"))


def has_complete_equity(payload: Any) -> bool:
    """Equity block must carry BOTH FII and DII activity (both buy/sell sides).

    Guards against partial upstream responses. Derivative excluded (cash-only source).
    """
    if not isinstance(payload, dict):
        return False
    eq = payload.get("equity")
    if not isinstance(eq, dict):
        return False
    fii_active = to_number(eq.get("fii_buy")) != 0 or to_number(eq.get("fii_sell")) != 0
    dii_active = to_number(eq.get("dii_buy")) != 0 or to_number(eq.get("dii_sell")) != 0
    return fii_active and dii_active


def parse_nse(arr: Any) -> dict[str, float]:
    """Parse the NSE /api/fiidii response into an equity block.

    Rows: {category, buyValue, sellValue, netValue}. FPI == FII; exclude DII row.
    """
    if not isinstance(arr, list):
        raise ValueError("NSE body is not an array")

    def _cat(r):
        return (r or {}).get("category", "") if isinstance(r, dict) else ""

    fii = next((r for r in arr if re.search(r"f(ii|pi)", _cat(r), re.I) and not re.match(r"\s*dii", _cat(r), re.I)), None)
    dii = next((r for r in arr if re.match(r"\s*dii", _cat(r), re.I)), None)
    fii = fii or {}
    dii = dii or {}
    return make_block(
        fii={"buy": fii.get("buyValue"), "sell": fii.get("sellValue"), "net": fii.get("netValue")},
        dii={"buy": dii.get("buyValue"), "sell": dii.get("sellValue"), "net": dii.get("netValue")},
    )


def parse_moneycontrol_row(cells: Any) -> dict[str, float]:
    """Parse one Moneycontrol FII/DII table row into an equity block.

    Table: Date | FII Buy | FII Sell | FII Net | DII Buy | DII Sell | DII Net.
    Numeric values start at index 1 (index 0 is the date).
    """
    if not isinstance(cells, list):
        raise ValueError("MC cells is not an array")
    c = cells + [None] * (7 - len(cells))
    _, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net = c[:7]
    return make_block(
        fii={"buy": fii_buy, "sell": fii_sell, "net": fii_net},
        dii={"buy": dii_buy, "sell": dii_sell, "net": dii_net},
    )


def parse_groww(next_data: Any) -> list[dict]:
    """Parse Groww __NEXT_DATA__ JSON into dated equity records, newest first.

    Shape: props.pageProps.initialData -> [{date, fii:{grossBuy,grossSell,netBuySell}, dii:{...}}]
    Returns [{date, equity}] preserving Groww's newest-first order.
    """
    if not isinstance(next_data, dict):
        raise ValueError("groww: NEXT_DATA is not an object")
    rows = next_data.get("props", {}).get("pageProps", {}).get("initialData")
    if not rows:
        raise ValueError("groww: initialData empty")
    out: list[dict] = []
    for row in rows:
        date = str(row.get("date") or "").strip()
        if not _DATE_RE.match(date):
            continue
        fii = row.get("fii") or {}
        dii = row.get("dii") or {}
        out.append(
            {
                "date": date,
                "equity": make_block(
                    fii={"buy": fii.get("grossBuy"), "sell": fii.get("grossSell"), "net": fii.get("netBuySell")},
                    dii={"buy": dii.get("grossBuy"), "sell": dii.get("grossSell"), "net": dii.get("netBuySell")},
                ),
            }
        )
    if not out:
        raise ValueError("groww: no dated rows parsed")
    return out
