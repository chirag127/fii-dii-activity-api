"""Build a dependency-free static site into dist/ for GitHub Pages.

Chart renders CLIENT-SIDE from live data (data/index.json + per-day JSON) so it
always reflects current data with no rebuild. Copies data/ + openapi.yaml verbatim.
Ported from scripts/build-site.mjs. Run: python -m fii_dii.build_site
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .manifest import write_manifest

_ENDPOINTS = [
    ("GitHub Pages (canonical)", "https://chirag127.github.io/fii-dii-activity-api/data/latest.json"),
    ("raw.githubusercontent.com", "https://raw.githubusercontent.com/chirag127/fii-dii-activity-api/main/data/latest.json"),
    ("jsDelivr CDN", "https://cdn.jsdelivr.net/gh/chirag127/fii-dii-activity-api@main/data/latest.json"),
    ("Statically CDN", "https://cdn.statically.io/gh/chirag127/fii-dii-activity-api/main/data/latest.json"),
]

_CLIENT_JS = """
async function loadChart() {
  const status = document.getElementById('chart-status');
  try {
    const idx = await (await fetch('data/index.json', { cache: 'no-store' })).json();
    const days = await Promise.all(
      idx.dates.map((d) => fetch('data/' + d + '.json', { cache: 'no-store' }).then((r) => r.json()))
    );
    days.sort((a, b) => a.date.localeCompare(b.date));
    render(days);
    const l = days[days.length - 1];
    status.innerHTML = 'Latest: <strong>' + l.date + '</strong> — FII net ' +
      l.equity.fii_net + ' cr, DII net ' + l.equity.dii_net + ' cr (source: ' + l.source +
      '). ' + days.length + ' sessions · rendered live from data/.';
  } catch (e) {
    status.textContent = 'Could not load live data: ' + e.message;
  }
}
function render(days) {
  const W = 720, H = 260, pad = 40;
  const fii = days.map((d) => d.equity.fii_net);
  const dii = days.map((d) => d.equity.dii_net);
  const all = fii.concat(dii, [0]);
  const min = Math.min.apply(null, all), max = Math.max.apply(null, all);
  const span = (max - min) || 1;
  const x = (i) => pad + (i * (W - 2 * pad)) / Math.max(days.length - 1, 1);
  const y = (v) => H - pad - ((v - min) / span) * (H - 2 * pad);
  const path = (arr) => arr.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join(' ');
  const svg = document.getElementById('chart');
  const zeroY = y(0).toFixed(1);
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.innerHTML =
    '<line x1="' + pad + '" y1="' + zeroY + '" x2="' + (W - pad) + '" y2="' + zeroY + '" stroke="#cbd5e1" stroke-dasharray="4 4"/>' +
    '<path d="' + path(fii) + '" fill="none" stroke="#2563eb" stroke-width="2"/>' +
    '<path d="' + path(dii) + '" fill="none" stroke="#f59e0b" stroke-width="2"/>' +
    '<text x="' + pad + '" y="18" font-size="13" fill="#2563eb">FII net</text>' +
    '<text x="' + (pad + 70) + '" y="18" font-size="13" fill="#f59e0b">DII net</text>';
}
loadChart();
""".strip()


def _html(rows_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FII/DII Activity API</title>
<meta name="description" content="Daily FII/DII net buy/sell activity for Indian equity markets, served as static JSON.">
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 820px; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }}
  h1 {{ margin-bottom: .2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #e2e8f0; font-size: .92rem; }}
  code {{ background: rgba(127,127,127,.15); padding: .1rem .3rem; border-radius: 4px; }}
  .meta {{ color: #64748b; font-size: .9rem; }}
  svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>FII/DII Activity API</h1>
<p class="meta">Daily FII (Foreign Institutional Investors) and DII (Domestic Institutional Investors) net buy/sell activity for Indian equity markets. Static JSON, no auth, all values in INR crore.</p>

<h2>FII vs DII net equity flow</h2>
<svg id="chart" role="img" aria-label="FII vs DII net equity flow"></svg>
<p class="meta" id="chart-status">Loading live data…</p>
<noscript><p class="meta">Enable JavaScript to see the live chart, or fetch <a href="data/latest.json"><code>data/latest.json</code></a> directly.</p></noscript>

<h2>Endpoints</h2>
<table>
<thead><tr><th>Source</th><th>Latest scrape URL</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<p class="meta">Specific day: replace <code>latest.json</code> with <code>&lt;YYYY-MM-DD&gt;.json</code>. Discover all dates via <a href="data/index.json"><code>data/index.json</code></a>. Machine-readable contract: <a href="./openapi.yaml"><code>openapi.yaml</code></a>.</p>

<h2>Response shape</h2>
<pre><code>{{
  "date": "YYYY-MM-DD",
  "source": "nse | groww | moneycontrol | placeholder",
  "equity":     {{ "fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net" }},
  "derivative": {{ ... same fields (currently always zero — cash-only source) }}
}}</code></pre>

<p class="meta"><a href="https://github.com/chirag127/fii-dii-activity-api">Source on GitHub</a> · MIT</p>
<script>{_CLIENT_JS}</script>
</body>
</html>
"""


def build(root: Path) -> int:
    data_dir = root / "data"
    dist = root / "dist"
    dist_data = dist / "data"
    dist_data.mkdir(parents=True, exist_ok=True)

    write_manifest(data_dir)  # ensure manifest present + current
    for f in data_dir.iterdir():
        if f.is_file():
            shutil.copyfile(f, dist_data / f.name)
    openapi = root / "openapi.yaml"
    if openapi.exists():
        shutil.copyfile(openapi, dist / "openapi.yaml")

    rows_html = "\n".join(
        f'<tr><td>{name}</td><td><a href="{url}"><code>{url}</code></a></td></tr>' for name, url in _ENDPOINTS
    )
    html = _html(rows_html)
    (dist / "index.html").write_text(html, encoding="utf-8")
    (dist / "404.html").write_text(html, encoding="utf-8")
    (dist / "CNAME").write_text("fii-dii-activity-api.oriz.in\n", encoding="utf-8")
    return sum(1 for _ in dist_data.iterdir())


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    n = build(root)
    print(f"Built dist/ (live client-side chart + {n} data files + openapi.yaml)")


if __name__ == "__main__":
    main()
