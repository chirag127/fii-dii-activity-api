#!/usr/bin/env node
/**
 * Builds the static FII/DII site into _site/.
 *
 * Source of truth is data/*.json (git-as-DB, committed by the scrape workflow).
 * The page is fully self-contained: inline CSS + inline SVG charts, zero runtime
 * dependencies, no CDN. All links are relative so the same artifact works at
 * /  (Cloudflare Pages) and /<repo>/  (GitHub Pages).
 */
import { readFileSync, readdirSync, mkdirSync, writeFileSync, cpSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dataDir = join(root, 'data');
const outDir = join(root, '_site');

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'));

const files = readdirSync(dataDir).filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort();
const series = files.map((f) => {
  const d = readJson(join(dataDir, f));
  return {
    date: d.date,
    fii: Number(d?.equity?.fii_net ?? 0),
    dii: Number(d?.equity?.dii_net ?? 0),
  };
});

if (series.length === 0) {
  console.error('no daily data files found in data/');
  process.exit(1);
}

const latest = series[series.length - 1];
const window30 = series.slice(-30);
const sum = (arr, k) => arr.reduce((a, x) => a + x[k], 0);
const crore = (n) => `${n >= 0 ? '+' : '\u2212'}${Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const short = (n) => {
  const a = Math.abs(n);
  const s = a >= 1000 ? `${(a / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : a.toFixed(0);
  return `${n > 0 ? '+' : n < 0 ? '\u2212' : ''}${s}`;
};
const mmdd = (iso) => iso.slice(5);

/* ---------- chart helpers ---------- */
const ESC = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function divergingBars(rows, { width = 980, height = 300, label = 'Net flows (₹ crore)' } = {}) {
  const pad = { t: 18, r: 16, b: 34, l: 76 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const max = Math.max(1, ...rows.flatMap((r) => [Math.abs(r.fii), Math.abs(r.dii)]));
  const scale = ih / 2 / max;
  const zero = pad.t + ih / 2;
  const slot = iw / rows.length;
  const bw = Math.max(2, Math.min(11, slot / 2.6));

  const bars = rows
    .map((r, i) => {
      const x = pad.l + i * slot + (slot - bw * 2 - 1) / 2;
      const fh = Math.abs(r.fii) * scale;
      const dh = Math.abs(r.dii) * scale;
      const fy = r.fii >= 0 ? zero - fh : zero;
      const dy = r.dii >= 0 ? zero - dh : zero;
      const tip = `${r.date} · FII ${crore(r.fii)} · DII ${crore(r.dii)}`;
      return `<g><title>${ESC(tip)}</title>
        <rect x="${x.toFixed(1)}" y="${fy.toFixed(1)}" width="${bw}" height="${fh.toFixed(1)}" rx="1.5" class="fii"/>
        <rect x="${(x + bw + 1).toFixed(1)}" y="${dy.toFixed(1)}" width="${bw}" height="${dh.toFixed(1)}" rx="1.5" class="dii"/></g>`;
    })
    .join('');

  const ticks = [-max, -max / 2, 0, max / 2, max].map((v) => {
    const y = zero - v * scale;
    return `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" class="grid"/>
      <text x="${pad.l - 8}" y="${(y + 4).toFixed(1)}" class="axis" text-anchor="end">${short(v)}</text>`;
  }).join('');

  const labels = rows
    .map((r, i) => {
      if (i % Math.ceil(rows.length / 7) !== 0 && i !== rows.length - 1) return '';
      return `<text x="${(pad.l + i * slot + slot / 2).toFixed(1)}" y="${height - 10}" class="axis" text-anchor="middle">${mmdd(r.date)}</text>`;
    })
    .join('');

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${ESC(label)}">
    ${ticks}<line x1="${pad.l}" x2="${width - pad.r}" y1="${zero}" y2="${zero}" class="zero"/>
    ${bars}${labels}
  </svg>`;
}

function cumulativeArea(rows, { width = 980, height = 260 } = {}) {
  const pad = { t: 22, r: 16, b: 30, l: 76 };
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  let cf = 0;
  let cd = 0;
  const pts = rows.map((r, i) => {
    cf += r.fii;
    cd += r.dii;
    return { x: pad.l + (rows.length === 1 ? iw / 2 : (i * iw) / (rows.length - 1)), f: cf, d: cd };
  });
  const vals = pts.flatMap((p) => [p.f, p.d, 0]);
  const rawMin = Math.min(...vals);
  const rawMax = Math.max(...vals);
  const gap = Math.max(1, rawMax - rawMin) * 0.08;
  const min = rawMin - gap;
  const max = rawMax + gap;
  const span = Math.max(1, max - min);
  const y = (v) => pad.t + ih - ((v - min) / span) * ih;
  const line = (k) => pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${y(p[k]).toFixed(1)}`).join(' ');
  const area = (k) => `${line(k)} L${pts[pts.length - 1].x.toFixed(1)},${y(min).toFixed(1)} L${pts[0].x.toFixed(1)},${y(min).toFixed(1)} Z`;

  const ticks = [min, min + span / 2, max].map(
    (v) => `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="grid"/>
      <text x="${pad.l - 8}" y="${(y(v) + 4).toFixed(1)}" class="axis" text-anchor="end">${short(v)}</text>`
  ).join('');

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Cumulative net flows">
    <defs>
      <linearGradient id="gf" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity=".28"/><stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="gd" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#fbbf24" stop-opacity=".22"/><stop offset="100%" stop-color="#fbbf24" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${ticks}
    <path d="${area('f')}" fill="url(#gf)"/><path d="${area('d')}" fill="url(#gd)"/>
    <path d="${line('f')}" class="ln fii"/><path d="${line('d')}" class="ln dii"/>
    <text x="${pad.l}" y="${height - 8}" class="axis">${mmdd(rows[0].date)}</text>
    <text x="${width - pad.r}" y="${height - 8}" class="axis" text-anchor="end">${mmdd(rows[rows.length - 1].date)}</text>
  </svg>`;
}

/* ---------- page ---------- */
const fiiCum = sum(window30, 'fii');
const diiCum = sum(window30, 'dii');
const tone = (n) => (n >= 0 ? 'up' : 'down');

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FII/DII Activity — daily institutional flows, Oriz</title>
<meta name="description" content="Daily FII and DII net buy/sell activity for Indian equities, ${series.length} sessions of history, served as a free static JSON API.">
<meta name="theme-color" content="#0b1220">
<style>
  :root{
    --bg:#0b1220; --panel:#111b2c; --panel-2:#16233a; --line:#22314b;
    --ink:#e6edf7; --muted:#8ea3bf; --fii:#38bdf8; --dii:#fbbf24;
    --up:#4ade80; --down:#f87171;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:
      radial-gradient(1100px 520px at 82% -12%,rgba(56,189,248,.10),transparent 60%),
      radial-gradient(900px 480px at 8% -20%,rgba(251,191,36,.07),transparent 55%),
      var(--bg);
    color:var(--ink);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;
    -webkit-font-smoothing:antialiased}
  .wrap{max-width:1040px;margin:0 auto;padding:0 20px}
  a{color:inherit}
  .brand{display:flex;align-items:center;gap:10px;padding:14px 0;border-bottom:1px solid var(--line);
    font-weight:700;letter-spacing:.01em}
  .brand span{color:var(--fii)}
  .brand .tag{margin-left:auto;font:11px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
  header.hero{padding:38px 0 12px}
  h1{margin:0;font-size:clamp(26px,4.4vw,40px);line-height:1.08;letter-spacing:-.02em}
  h1 em{font-style:normal;color:var(--fii)}
  .sub{color:var(--muted);max-width:64ch;margin:12px 0 0}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:26px 0 8px}
  .kpi{background:linear-gradient(180deg,var(--panel),var(--panel-2));border:1px solid var(--line);
    border-radius:14px;padding:14px 16px}
  .kpi .k{font:11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .kpi .v{font:600 26px/1.2 var(--mono);margin:8px 0 2px;font-variant-numeric:tabular-nums}
  .kpi .d{font-size:12px;color:var(--muted)}
  .up{color:var(--up)} .down{color:var(--down)}
  section{margin:34px 0}
  .card{background:rgba(17,27,44,.72);border:1px solid var(--line);border-radius:16px;padding:16px 14px 8px}
  .card h2{margin:2px 6px 12px;font-size:14px;letter-spacing:.02em;font-weight:600}
  .legend{display:flex;gap:16px;margin:0 6px 6px;font:12px/1 var(--mono);color:var(--muted);flex-wrap:wrap}
  .legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px}
  .legend .f i{background:var(--fii)} .legend .d i{background:var(--dii)}
  svg{width:100%;height:auto;display:block}
  svg .grid{stroke:#22314b;stroke-width:1;stroke-dasharray:3 4}
  svg .zero{stroke:#3b4f70;stroke-width:1}
  svg .axis{fill:#7d92b0;font:11px var(--mono)}
  svg .fii{fill:var(--fii)} svg .dii{fill:var(--dii)}
  svg .ln{fill:none;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
  svg .ln.fii{stroke:var(--fii)} svg .ln.dii{stroke:var(--dii)}
  table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
  th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:right;font:13px var(--mono)}
  th:first-child,td:first-child{text-align:left}
  thead th{color:var(--muted);font-weight:500;font-size:11px;letter-spacing:.12em;text-transform:uppercase}
  tbody tr:hover{background:rgba(56,189,248,.05)}
  .api{display:grid;gap:10px}
  code,pre{font-family:var(--mono)}
  pre{background:#0a1120;border:1px solid var(--line);border-radius:12px;padding:14px;overflow:auto;font-size:12.5px;margin:0}
  .links{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
  .links a{color:var(--fii);text-decoration:none}
  .links a:hover{text-decoration:underline}
  footer{border-top:1px solid var(--line);margin-top:44px;padding:20px 0 44px;color:var(--muted);font-size:12.5px}
  @media (prefers-reduced-motion:no-preference){.kpi,.card{transition:border-color .2s}.kpi:hover,.card:hover{border-color:#2c3f5e}}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand">oriz<span>.in</span><span class="tag">FII / DII activity</span></div>

  <header class="hero">
    <h1>Who moved the Indian market <em>today</em>.</h1>
    <p class="sub">Daily net buy/sell activity for Foreign Institutional Investors and Domestic Institutional
      Investors, scraped after NSE close. ${series.length} sessions archived, served as a free static JSON API.</p>
  </header>

  <div class="kpis">
    <div class="kpi"><div class="k">FII net · latest</div>
      <div class="v ${tone(latest.fii)}">${crore(latest.fii)}<small> cr</small></div>
      <div class="d">${latest.date}</div></div>
    <div class="kpi"><div class="k">DII net · latest</div>
      <div class="v ${tone(latest.dii)}">${crore(latest.dii)}<small> cr</small></div>
      <div class="d">${latest.date}</div></div>
    <div class="kpi"><div class="k">FII cumulative · ${window30.length}d</div>
      <div class="v ${tone(fiiCum)}">${crore(fiiCum)}<small> cr</small></div>
      <div class="d">${window30[0].date} → ${latest.date}</div></div>
    <div class="kpi"><div class="k">DII cumulative · ${window30.length}d</div>
      <div class="v ${tone(diiCum)}">${crore(diiCum)}<small> cr</small></div>
      <div class="d">${window30[0].date} → ${latest.date}</div></div>
  </div>

  <section>
    <div class="card">
      <h2>Daily net flows — last ${window30.length} sessions</h2>
      <div class="legend"><span class="f"><i></i>FII</span><span class="d"><i></i>DII</span></div>
      ${divergingBars(window30)}
    </div>
  </section>

  <section>
    <div class="card">
      <h2>Cumulative institutional flow — full archive</h2>
      <div class="legend"><span class="f"><i></i>FII cumulative</span><span class="d"><i></i>DII cumulative</span></div>
      ${cumulativeArea(series)}
    </div>
  </section>

  <section>
    <div class="card" style="padding:16px">
      <h2 style="margin-bottom:8px">Recent sessions</h2>
      <table>
        <thead><tr><th>Date</th><th>FII net</th><th>DII net</th><th>Combined</th></tr></thead>
        <tbody>${series.slice(-12).reverse().map((r) => `<tr>
          <td>${r.date}</td>
          <td class="${tone(r.fii)}">${crore(r.fii)}</td>
          <td class="${tone(r.dii)}">${crore(r.dii)}</td>
          <td class="${tone(r.fii + r.dii)}">${crore(r.fii + r.dii)}</td></tr>`).join('')}
        </tbody>
      </table>
    </div>
  </section>

  <section class="api">
    <div class="card" style="padding:16px">
      <h2 style="margin-bottom:10px">API</h2>
      <pre>GET api/v1/data.json      # every session, full payload
GET api/v1/index.json     # date index
GET data/latest.json      # latest session only</pre>
      <div class="links" style="margin-top:14px">
        <a href="openapi.yaml">openapi.yaml</a>
        <a href="schemas/">schemas</a>
        <a href="https://github.com/chirag127/fii-dii-activity-api">source</a>
        <a href="https://oriz.in">oriz.in</a>
      </div>
    </div>
  </section>

  <footer>Figures in ₹ crore, cash-market equity segment, source Groww.
    Data is unofficial and provided as-is — not investment advice.</footer>
</div>
</body>
</html>`;

mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, 'index.html'), html);

for (const d of ['api', 'schemas', 'data']) {
  if (existsSync(join(root, d))) cpSync(join(root, d), join(outDir, d), { recursive: true });
}
for (const f of ['openapi.yaml', 'README.md', 'LICENSE', 'SECURITY.md']) {
  if (existsSync(join(root, f))) cpSync(join(root, f), join(outDir, f));
}

console.log(`built _site/index.html from ${series.length} sessions (latest ${latest.date})`);
