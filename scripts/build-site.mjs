// Build a minimal, dependency-free static site into dist/ for GitHub Pages.
// The chart is rendered CLIENT-SIDE from live data (data/index.json + per-day
// JSON) so it always reflects current data with no rebuild — nothing about the
// series is baked into the HTML. Copies data/ and openapi.yaml verbatim.
// No external template, no build tooling. Run: node scripts/build-site.mjs
import { writeFileSync, mkdirSync, readdirSync, copyFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dataDir = join(root, 'data');
const dist = join(root, 'dist');
const distData = join(dist, 'data');

mkdirSync(distData, { recursive: true });

// Ensure the manifest the browser needs is present and current.
execFileSync(process.execPath, [join(root, 'scripts', 'manifest.mjs')], { stdio: 'inherit' });

// Copy all data files (incl. index.json) + openapi.yaml verbatim.
for (const f of readdirSync(dataDir)) copyFileSync(join(dataDir, f), join(distData, f));
if (existsSync(join(root, 'openapi.yaml'))) copyFileSync(join(root, 'openapi.yaml'), join(dist, 'openapi.yaml'));

const rows = [
  ['GitHub Pages (canonical)', 'https://chirag127.github.io/fii-dii-activity-api/data/latest.json'],
  ['raw.githubusercontent.com', 'https://raw.githubusercontent.com/chirag127/fii-dii-activity-api/main/data/latest.json'],
  ['jsDelivr CDN', 'https://cdn.jsdelivr.net/gh/chirag127/fii-dii-activity-api@main/data/latest.json'],
  ['Statically CDN', 'https://cdn.statically.io/gh/chirag127/fii-dii-activity-api/main/data/latest.json'],
]
  .map(([name, url]) => `<tr><td>${name}</td><td><a href="${url}"><code>${url}</code></a></td></tr>`)
  .join('\n');

// Client-side renderer: fetch the manifest, then every day's payload, then draw
// an inline SVG of FII vs DII net. Runs on each page load — always current.
const clientScript = `
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
`.trim();

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FII/DII Activity API</title>
<meta name="description" content="Daily FII/DII net buy/sell activity for Indian equity markets, served as static JSON.">
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 820px; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }
  h1 { margin-bottom: .2rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #e2e8f0; font-size: .92rem; }
  code { background: rgba(127,127,127,.15); padding: .1rem .3rem; border-radius: 4px; }
  .meta { color: #64748b; font-size: .9rem; }
  svg { max-width: 100%; height: auto; }
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
${rows}
</tbody>
</table>
<p class="meta">Specific day: replace <code>latest.json</code> with <code>&lt;YYYY-MM-DD&gt;.json</code>. Discover all dates via <a href="data/index.json"><code>data/index.json</code></a>. Machine-readable contract: <a href="./openapi.yaml"><code>openapi.yaml</code></a>.</p>

<h2>Response shape</h2>
<pre><code>{
  "date": "YYYY-MM-DD",
  "source": "nse | moneycontrol | placeholder",
  "equity":     { "fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net" },
  "derivative": { ... same fields (currently always zero — NSE fiidii is cash-only) }
}</code></pre>

<p class="meta"><a href="https://github.com/chirag127/fii-dii-activity-api">Source on GitHub</a> · MIT</p>
<script>${clientScript}</script>
</body>
</html>
`;

writeFileSync(join(dist, 'index.html'), html);
writeFileSync(join(dist, '404.html'), html);
writeFileSync(join(dist, 'CNAME'), 'fii-dii-activity-api.oriz.in
');
console.log(`Built dist/ (live client-side chart + ${readdirSync(distData).length} data files + openapi.yaml)`);
