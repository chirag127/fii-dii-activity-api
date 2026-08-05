"""Chart generator + README chart-marker tests. Ported from scripts/chart.test.mjs."""

import re


def _readme(root):
    return (root / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")


def test_readme_has_chart_markers_and_mermaid(root):
    r = _readme(root)
    assert "<!-- CHART:BEGIN -->" in r
    assert "<!-- CHART:END -->" in r
    assert re.search(r"```mermaid\n\s*xychart-beta", r)


def test_chart_y_axis_non_degenerate(root):
    m = re.search(r'y-axis\s+"[^"]*"\s+(-?\d+)\s+-->\s+(-?\d+)', _readme(root))
    assert m, "y-axis range not found"
    lo, hi = int(m.group(1)), int(m.group(2))
    assert hi > lo, f"y-axis must be non-degenerate, got {lo} --> {hi}"


def test_chart_has_two_series_and_x_axis(root):
    r = _readme(root)
    assert re.search(r"x-axis \[", r)
    lines = re.findall(r"^\s*line \[", r, re.M)
    assert len(lines) == 2, "expected exactly two series (FII, DII)"


def test_build_chart_handles_all_zero():
    from fii_dii.chart import build_chart

    days = [{"date": "2026-07-01", "equity": {"fii_net": 0, "dii_net": 0}}]
    out = build_chart(days)
    m = re.search(r"-->\s*(-?\d+)", out)
    lo = re.search(r'y-axis\s+"[^"]*"\s+(-?\d+)\s+-->\s+(-?\d+)', out)
    assert lo and int(lo.group(2)) > int(lo.group(1)), "degenerate axis must be padded"
