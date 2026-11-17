"""Backfill data/<date>.json from every dated row the Groww page exposes.

The daily scrape only writes the newest session. Groww's server-rendered
__NEXT_DATA__ carries the last ~20 sessions, so a single pull can heal gaps left
by failed runs (bad selector, dependency upgrade, skipped cron).

Run: python -m fii_dii.backfill [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scrape import try_groww_payloads
from .schema import build_payload, has_complete_equity, validate_payload, zero_block
from .util import configure_logging, log


def load_records() -> list[dict]:
    return try_groww_payloads()


def backfill(data_dir: Path, dry_run: bool = False) -> list[str]:
    records = load_records()
    data_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for rec in records:
        date = rec["date"]
        payload = build_payload(
            date=date, source="groww", equity=rec["equity"], derivative=zero_block()
        )
        ok, errors = validate_payload(payload)
        if not ok or not has_complete_equity(payload):
            log.error("skip %s: %s", date, "; ".join(errors) or "incomplete equity")
            continue
        target = data_dir / f"{date}.json"
        if target.exists():
            continue
        if not dry_run:
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(date)

    dates = sorted(p.stem for p in data_dir.glob("*.json") if p.stem[:4].isdigit())
    if dates and not dry_run:
        latest = json.loads((data_dir / f"{dates[-1]}.json").read_text(encoding="utf-8"))
        (data_dir / "latest.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")

    log.info("backfilled %d session(s): %s", len(written), ", ".join(written) or "none")
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill FII/DII history from Groww")
    ap.add_argument("--data", default="data")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    configure_logging(args.verbose)
    backfill(Path(args.data), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
