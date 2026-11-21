"""Dashboard: a single static HTML page (no build step, no CDN) served
by the API at /dashboard. It talks to the JSON API with fetch():
corpus stats (/stats), search (/search), ask (/ask), graph (/graph).
"""
from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ARGUS-AI Dashboard</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 900px;
         padding: 0 1rem; background: #0d1117; color: #e6edf3; }
  h1 { font-size: 1.5rem; } h2 { font-size: 1.1rem; margin-top: 2rem; }
  .cards { display: flex; gap: 1rem; flex-wrap: wrap; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
          padding: 1rem 1.25rem; min-width: 120px; }
  .card b { font-size: 1.6rem; display: block; }
  input, button { font-size: 1rem; padding: .45rem .6rem; border-radius: 6px;
                  border: 1px solid #30363d; background: #161b22; color: #e6edf3; }
  button { cursor: pointer; background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .hit, .risk { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                padding: .7rem 1rem; margin: .5rem 0; }
  .score { color: #7ee787; font-weight: 600; }
  .high { color: #ff7b72; } .medium { color: #e3b341; } .low { color: #7ee787; }
  small { color: #8b949e; }
</style>
</head>
<body>
<h1>👁️ ARGUS-AI <small id="ver"></small></h1>

<h2>Corpus</h2>
<div class="cards" id="stats"><div class="card">loading…</div></div>

<h2>Search / Ask</h2>
<input id="q" size="52" placeholder="e.g. bitcoin treasury policy">
<button onclick="doSearch()">Search</button>
<button onclick="doAsk()">Ask (Graph RAG)</button>
<div id="results"></div>

<h2>Risk list (GUARDIAN)</h2>
<div id="risks"></div>

<h2>Knowledge graph (ATLAS)</h2>
<div id="graph"><small>loading…</small></div>

<script>
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function loadStats() {
  const s = await (await fetch('/stats')).json();
  document.getElementById('ver').textContent = 'v' + (s.version || '');
  document.getElementById('stats').innerHTML =
    [['Documents', s.documents], ['Chunks', s.chunks],
     ['Entities', s.entities], ['Relations', s.relations]]
    .map(([k, v]) => `<div class="card"><b>${v}</b>${k}</div>`).join('');
  document.getElementById('risks').innerHTML = (s.risk_list || []).map(r =>
    `<div class="risk"><span class="${r.risk_level}"><b>${r.risk_score}</b></span>
     ${esc(r.doc_id)} <small>${esc(r.category)} · ${esc(r.risk_level)}</small></div>`
  ).join('') || '<small>no assessed documents yet</small>';
  const g = await (await fetch('/graph')).json();
  const graph = g.graph || {};
  document.getElementById('graph').innerHTML =
    `<small>${(graph.nodes || []).length} nodes ·
     ${(graph.relations || []).length} relations ·
     top entities: ${esc((graph.nodes || []).slice(0, 12).join(', '))}</small>`;
}

async function doSearch() {
  const q = document.getElementById('q').value;
  const r = await (await fetch('/search?q=' + encodeURIComponent(q))).json();
  document.getElementById('results').innerHTML = (r.results || []).map(h =>
    `<div class="hit"><span class="score">${h.score}</span> ${esc(h.doc_id)}
     <br><small>${esc(h.text)}</small></div>`).join('');
}

async function doAsk() {
  const q = document.getElementById('q').value;
  const r = await (await fetch('/ask?q=' + encodeURIComponent(q))).json();
  const res = r.result || {};
  document.getElementById('results').innerHTML =
    `<div class="hit"><b>Answer</b> <small>(${esc(res.mode || '')})</small>` +
    `<br>${esc(res.answer || '')}<br><small>citations: ` +
    `${esc((res.citations || []).join(', '))}</small></div>`;
}

loadStats();
</script>
</body>
</html>
"""
