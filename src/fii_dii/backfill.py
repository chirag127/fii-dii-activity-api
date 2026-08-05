"""One-off backfill of historical FII/DII cash-segment data.

The pre-fix scraper committed all-zero files for these dates; this repopulates
them with real provisional figures (cross-verified across Groww, Kotak Neo,
Sensibull, Multibagg, Sahifund — all agree on CM cash buy/sell/net, INR crore).
Derivative stays zero. Ported from scripts/backfill.mjs.
Run once: python -m fii_dii.backfill
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .schema import build_payload, make_block, validate_payload, zero_block

# (date, fiiBuy, fiiSell, fiiNet, diiBuy, diiSell, diiNet)
ROWS = [
    ("2026-06-22", 10082.08, 10717.99, -635.91, 17391.78, 16356.06, 1035.72),
    ("2026-06-23", 15396.07, 15378.21, 17.86, 16863.04, 16182.83, 680.21),
    ("2026-06-24", 16744.73, 18588.13, -1843.40, 17274.01, 13636.75, 3637.26),
    ("2026-07-02", 14018.40, 14330.22, -311.82, 17391.61, 15607.21, 1784.40),
    ("2026-07-03", 13337.33, 11982.00, 1355.33, 18676.35, 20630.24, -1953.89),
    ("2026-07-06", 11686.10, 11443.07, 243.03, 19727.56, 15936.14, 3791.42),
    ("2026-07-07", 18414.01, 18020.82, 393.19, 18897.44, 19280.87, -383.43),
    ("2026-07-08", 17463.95, 15501.15, 1962.80, 19165.13, 18374.97, 790.16),
    ("2026-07-09", 14388.41, 14921.27, -532.86, 18302.87, 16245.08, 2057.79),
    ("2026-07-10", 15318.07, 12714.35, 2603.72, 17171.75, 15152.07, 2019.68),
    ("2026-07-13", 10386.48, 13448.75, -3062.27, 17393.46, 15221.76, 2171.70),
    ("2026-07-14", 12763.43, 13503.12, -739.69, 20420.87, 17493.16, 2927.71),
    ("2026-07-15", 13207.46, 13943.29, -735.83, 16226.42, 15521.49, 704.93),
    ("2026-07-16", 13576.08, 17781.64, -4205.56, 19236.80, 16250.39, 2986.41),
    ("2026-07-17", 14393.77, 14770.18, -376.41, 17180.08, 16162.19, 1017.89),
    ("2026-07-20", 13312.67, 14433.71, -1121.04, 16187.84, 14875.81, 1312.03),
    ("2026-07-21", 16327.88, 14677.72, 1650.16, 14638.54, 15295.42, -656.88),
]


def backfill(data_dir: Path) -> dict | None:
    latest = None
    for date, fb, fs, fn, db, ds, dn in ROWS:
        payload = build_payload(
            date=date,
            source="moneycontrol",
            equity=make_block(fii={"buy": fb, "sell": fs, "net": fn}, dii={"buy": db, "sell": ds, "net": dn}),
            derivative=zero_block(),
        )
        ok, errors = validate_payload(payload)
        if not ok:
            print(f"REFUSING to write {date}: {'; '.join(errors)}", file=sys.stderr)
            continue
        (data_dir / f"{date}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        latest = payload
    if latest:
        (data_dir / "latest.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    return latest


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    latest = backfill(data_dir)
    if latest:
        print(f"Backfilled {len(ROWS)} files; latest.json -> {latest['date']}")


if __name__ == "__main__":
    main()
