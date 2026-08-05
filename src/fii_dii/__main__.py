"""CLI: scrape FII/DII -> data/<date>.json + data/latest.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .schema import build_payload, has_complete_equity, validate_payload
from .scrape import try_groww, try_moneycontrol, try_nse
from .util import configure_logging, log


def try_source(name: str, fn, today: str) -> dict | None:
    """Run a source; return payload only if it validates AND has complete FII+DII."""
    try:
        payload = fn(today)
    except Exception as e:  # noqa: BLE001 — any failure -> try next source
        log.error("%s failed: %s", name, e)
        return None
    ok, errors = validate_payload(payload)
    if not ok:
        log.error("%s produced invalid payload: %s", name, "; ".join(errors))
        return None
    if not has_complete_equity(payload):
        log.error("%s missing FII and/or DII equity data — treating as failure", name)
        return None
    return payload


def scrape(today: str) -> dict:
    sources = [("NSE", try_nse), ("Groww", try_groww), ("Moneycontrol", try_moneycontrol)]
    for name, fn in sources:
        payload = try_source(name, fn, today)
        if payload is not None:
            return payload
    return build_payload(date=today, source="placeholder")


def write_payload(payload: dict, data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    dated = data_dir / f"{payload['date']}.json"
    dated.write_text(text, encoding="utf-8")
    (data_dir / "latest.json").write_text(text, encoding="utf-8")
    return dated


def run(data_dir: Path) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    payload = scrape(today)
    dated = write_payload(payload, data_dir)
    log.info("wrote %s source=%s", dated, payload["source"])
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape India FII/DII daily activity")
    ap.add_argument("--data", default="data", help="output dir (default: data)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    configure_logging(args.verbose)
    run(Path(args.data))


if __name__ == "__main__":
    main()
