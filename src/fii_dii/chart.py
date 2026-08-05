"""Regenerate the FII/DII net-activity Mermaid chart in README.md from data/*.json.

GitHub-native xychart-beta (no external service): FII net vs DII net (INR crore)
over the most recent sessions, between the CHART markers. Ported from scripts/chart.mjs.
Run: python -m fii_dii.chart
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

MAX_POINTS = 20
BEGIN = "<!-- CHART:BEGIN -->"
END = "<!-- CHART:END -->"
_DATED = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def load_days(data_dir: Path) -> list[dict]:
    files = sorted(f for f in data_dir.glob("*.json") if _DATED.match(f.name))[-MAX_POINTS:]
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def build_chart(days: list[dict]) -> str:
    if not days:
        return f"{BEGIN}\n_No data yet._\n{END}"
    labels = [f'"{d["date"][5:]}"' for d in days]  # MM-DD
    fii = [d["equity"]["fii_net"] for d in days]
    dii = [d["equity"]["dii_net"] for d in days]
    all_vals = fii + dii + [0]
    lo, hi = math.floor(min(all_vals)), math.ceil(max(all_vals))
    if lo == hi:  # Mermaid rejects a zero-height axis
        lo -= 1
        hi += 1
    return "\n".join(
        [
            BEGIN,
            "**FII vs DII net equity flow (₹ crore, most recent sessions)**",
            "",
            "```mermaid",
            "xychart-beta",
            '    title "FII net (line 1) vs DII net (line 2) — INR crore"',
            f"    x-axis [{', '.join(labels)}]",
            f'    y-axis "Net (INR cr)" {lo} --> {hi}',
            f"    line [{', '.join(_fmt(v) for v in fii)}]",
            f"    line [{', '.join(_fmt(v) for v in dii)}]",
            "```",
            "",
            f"<sub>FII = first line, DII = second line. Auto-generated from `data/` by `python -m fii_dii.chart` on each scrape. Last {len(days)} session(s).</sub>",
            END,
        ]
    )


def update_readme(readme_path: Path, data_dir: Path) -> bool:
    readme = readme_path.read_text(encoding="utf-8")
    chart = build_chart(load_days(data_dir))
    if BEGIN in readme and END in readme:
        nxt = re.sub(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END), lambda _: chart, readme)
    else:
        anchor = "\n## Endpoints"
        idx = readme.find(anchor)
        nxt = (
            f"{readme}\n\n## Chart\n\n{chart}\n"
            if idx == -1
            else f"{readme[:idx]}\n## Chart\n\n{chart}\n{readme[idx:]}"
        )
    if nxt != readme:
        readme_path.write_text(nxt, encoding="utf-8")
        return True
    return False


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    changed = update_readme(root / "README.md", root / "data")
    print("README chart updated." if changed else "README chart already current.")


if __name__ == "__main__":
    main()
