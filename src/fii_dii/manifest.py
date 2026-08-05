"""Generate data/index.json — a manifest of every dated payload for client-side discovery.

Fully dynamic; no hardcoding. Ported from scripts/manifest.mjs.
Run: python -m fii_dii.manifest
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DATED = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def build_manifest(data_dir: Path) -> dict:
    dates = sorted(f.stem for f in data_dir.glob("*.json") if _DATED.match(f.name))
    latest = None
    latest_file = data_dir / "latest.json"
    if latest_file.exists():
        try:
            latest = json.loads(latest_file.read_text(encoding="utf-8")).get("date")
        except (ValueError, OSError):
            latest = None
    if latest is None:
        latest = dates[-1] if dates else None
    return {"count": len(dates), "latest": latest, "dates": dates}


def write_manifest(data_dir: Path) -> dict:
    manifest = build_manifest(data_dir)
    (data_dir / "index.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    m = write_manifest(data_dir)
    print(f"Wrote data/index.json ({m['count']} dates, latest {m['latest']}).")


if __name__ == "__main__":
    main()
