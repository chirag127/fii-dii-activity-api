"""Validate every committed data file against the schema.

Catches the 2026-07-21 all-zero bug; guarantees latest.json mirrors newest dated
file. Ported from scripts/data.test.mjs.
"""

import json
import re

import pytest

from fii_dii.schema import has_data, validate_payload

_DATED = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def _payload_files(data_dir):
    return [f for f in data_dir.glob("*.json") if f.name != "index.json"]


def _dated_files(data_dir):
    return sorted(f for f in data_dir.glob("*.json") if _DATED.match(f.name))


def test_data_dir_has_files(data_dir):
    files = _payload_files(data_dir)
    assert files, "no data files found"
    assert (data_dir / "latest.json") in files or any(f.name == "latest.json" for f in files)


def test_all_payloads_are_valid(data_dir):
    for f in _payload_files(data_dir):
        payload = json.loads(f.read_text(encoding="utf-8"))
        ok, errors = validate_payload(payload)
        assert ok, f"{f.name}: {'; '.join(errors)}"


def test_dated_filename_matches_payload_date(data_dir):
    for f in _dated_files(data_dir):
        payload = json.loads(f.read_text(encoding="utf-8"))
        assert payload["date"] == f.stem


def test_latest_mirrors_newest_dated(data_dir):
    latest = json.loads((data_dir / "latest.json").read_text(encoding="utf-8"))
    dated = _dated_files(data_dir)
    newest = dated[-1].stem
    assert latest["date"] == newest
    newest_payload = json.loads((data_dir / f"{newest}.json").read_text(encoding="utf-8"))
    assert latest == newest_payload


def test_coverage_report(data_dir, capsys):
    dated = _dated_files(data_dir)
    with_data = [f for f in dated if has_data(json.loads(f.read_text(encoding="utf-8")))]
    ratio = (len(with_data) / len(dated) * 100) if dated else 0
    print(f"data coverage: {len(with_data)}/{len(dated)} dated files have non-zero data ({ratio:.0f}%)")
    assert len(dated) >= 0
