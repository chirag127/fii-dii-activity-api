"""Manifest must be dynamically derived from actual data files; regen = no drift.

Ported from scripts/manifest.test.mjs.
"""

import json
import re

_DATED = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def _actual_dates(data_dir):
    return sorted(f.stem for f in data_dir.glob("*.json") if _DATED.match(f.name))


def test_index_lists_exactly_the_dated_files(data_dir):
    manifest = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    assert manifest["dates"] == _actual_dates(data_dir), "manifest drifted — run python -m fii_dii.manifest"
    assert manifest["count"] == len(_actual_dates(data_dir))


def test_manifest_latest_matches_latest_json(data_dir):
    manifest = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    latest = json.loads((data_dir / "latest.json").read_text(encoding="utf-8"))
    assert manifest["latest"] == latest["date"]


def test_every_manifest_date_resolves(data_dir):
    manifest = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    for d in manifest["dates"]:
        payload = json.loads((data_dir / f"{d}.json").read_text(encoding="utf-8"))
        assert payload["date"] == d


def test_regenerating_manifest_produces_no_change(data_dir):
    from fii_dii.manifest import build_manifest

    on_disk = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    assert build_manifest(data_dir) == on_disk
