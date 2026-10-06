"""Write the results as an interactive web page (and a CSV backup).

Output goes to docs/ so GitHub Pages can serve it at a public URL.

The page embeds today's offers as data and renders them in the browser.
Your choices (Pas intéressé / Postulé / À garder, application status,
notes) are stored in the browser (localStorage), keyed by offer id, so
they survive the daily refresh. Offers you applied to are saved with
their title/company/link, so they stay in "Candidatures" even after the
offer disappears from the job sites.
"""
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "docs"

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

CSS = r"""
:root{
  --bg:#f5f6f8; --card:#fff; --ink:#18212b; --muted:#5f6b78; --line:#e6e9ee;
  --accent:#1f5eff; --accent-ink:#fff; --chip:#eef1f5; --hover:#f3f6ff;
  --new-bg:#e1f7e7; --new:#137333; --vie-bg:#fff1d1; --vie:#7a5600;
  --grad-bg:#ece7ff; --grad:#4b2fb3; --visa-bg:#dff1ff; --visa:#0b5394;
  --nodate-bg:#eef1f4; --nodate:#5f6b78; --ok:#137333; --ko:#b3261e;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0f141a; --card:#171e26; --ink:#e7ecf2; --muted:#98a4b2; --line:#26303b;
    --accent:#6b93ff; --accent-ink:#0b1020; --chip:#202a35; --hover:#1c2632;
    --new-bg:#163a22; --new:#7fd99a; --vie-bg:#3a2e12; --vie:#f2c66d;
    --grad-bg:#2a2347; --grad:#bfb0ff; --visa-bg:#13304a; --visa:#8cc8ff;
    --nodate-bg:#222b35; --nodate:#98a4b2; --ok:#7fd99a; --ko:#ff8a80;
    --shadow:none;
  }
}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;background:var(--bg);color:var(--ink);font-size:14px}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
header h1{font-size:22px;margin:4px 0 2px} .sub{color:var(--muted);margin:0 0 12px}
nav.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:12px;overflow-x:auto;scrollbar-width:none}
nav.tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:9px 12px;font:inherit;color:var(--muted);cursor:pointer;white-space:nowrap}
nav.tabs button.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
nav.tabs .n{display:inline-block;min-width:20px;padding:0 6px;margin-left:4px;border-radius:10px;background:var(--chip);font-size:12px;text-align:center}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.toolbar input[type=search],.toolbar select{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}
.toolbar input[type=search]{flex:1;min-width:180px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.chip{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:5px 10px;border-radius:999px;cursor:pointer}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.chip .c{opacity:.7;margin-left:3px}
.count{color:var(--muted);font-size:13px;margin:0 0 8px}
.list{display:flex;flex-direction:column;gap:8px}
.offer{display:flex;gap:12px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;box-shadow:var(--shadow)}
.offer:hover{background:var(--hover)}
.offer .main{flex:1;min-width:0}
.line1{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}
.title{font-weight:600;font-size:15px}
.score{font-weight:800;font-size:12px;min-width:30px;text-align:center;border-radius:6px;padding:1px 5px;background:var(--chip);color:var(--muted)}
.score.s-hi{background:var(--new-bg);color:var(--new)} .score.s-mid{background:var(--vie-bg);color:var(--vie)}
.pay{color:var(--ok);font-weight:600}
.prep{font-size:12px;margin-top:6px}
.meta{color:var(--muted);font-size:13px;margin-top:3px;display:flex;flex-wrap:wrap;gap:0 10px}
.meta b{color:var(--ink);font-weight:600}
details.why{margin-top:4px}
details.why summary{cursor:pointer;color:var(--muted);font-size:12px;list-style:none}
details.why summary::-webkit-details-marker{display:none}
details.why summary::before{content:'▸ ';}
details.why[open] summary::before{content:'▾ ';}
details.why p{margin:6px 0 0;font-size:13px;line-height:1.45}
.reasons span{display:inline-block;background:var(--chip);border-radius:6px;padding:1px 6px;margin:0 4px 3px 0;font-size:12px}
.actions{display:flex;gap:6px;flex-shrink:0}
.btn{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 10px;cursor:pointer;white-space:nowrap}
.btn:hover{border-color:var(--muted)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.btn.star.on{color:#d49b00;border-color:#d49b00}
.badge{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700;letter-spacing:.2px}
.b-new{background:var(--new-bg);color:var(--new)} .b-vie{background:var(--vie-bg);color:var(--vie)}
.b-grad{background:var(--grad-bg);color:var(--grad)} .b-visa{background:var(--visa-bg);color:var(--visa)}
.b-nodate{background:var(--nodate-bg);color:var(--nodate)}
.empty{text-align:center;color:var(--muted);padding:40px 10px;background:var(--card);border:1px dashed var(--line);border-radius:10px}
table.compact{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
table.compact th,table.compact td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);font-size:13px;vertical-align:middle}
table.compact th{color:var(--muted);font-weight:600;background:var(--chip)}
table.compact select,table.compact input{font:inherit;font-size:13px;padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
table.compact input.note{width:100%;min-width:120px}
.tablewrap{overflow-x:auto}
.st-Entretien,.st-Test{color:#0b5394;font-weight:600} .st-Offre{color:var(--ok);font-weight:700} .st-Refusé{color:var(--ko)}
.pipeline{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.pipeline div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:13px}
.pipeline b{font-size:16px;margin-right:4px}
.ok{color:var(--ok)} .ko{color:var(--ko)}
footer{margin:26px 0 10px;color:var(--muted);font-size:12px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
footer .btn{font-size:12px;padding:4px 8px}
#toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%) translateY(120px);background:#18212b;color:#fff;padding:10px 14px;border-radius:10px;display:flex;gap:14px;align-items:center;transition:transform .2s;z-index:10;box-shadow:0 4px 18px rgba(0,0,0,.25);font-size:14px}
#toast.show{transform:translateX(-50%) translateY(0)}
#toast button{background:none;border:0;color:#8fb0ff;font:inherit;font-weight:700;cursor:pointer}
.hidden{display:none!important}
.kbd{font-family:ui-monospace,monospace;font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px}
@media (max-width:640px){
  .wrap{padding:10px}
  .offer{flex-direction:column;gap:8px}
  .actions{width:100%}
  .actions .btn{flex:1;text-align:center}
  .actions .btn.star{flex:0 0 auto}
  .hide-sm{display:none}
}
"""

JS = r"""
(function(){
var OFFERS = JSON.parse(document.getElementById('data-offers').textContent);
var KEY = 'jd_state_v1', UIKEY = 'jd_ui_v1';
function load(k, d){ try { var v = JSON.parse(localStorage.getItem(k)); return v || d; } catch(e){ return d; } }
function save(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} }
var S = load(KEY, {});      // id -> {s:'hidden'|'applied'|'saved', t:'YYYY-MM-DD', o:{...}, st, note}
var UI = load(UIKEY, {});
UI.tab = UI.tab || 'todo'; UI.chips = UI.chips || []; UI.sort = UI.sort || 'score'; UI.q = '';
var byId = {}; OFFERS.forEach(function(o){ byId[o.id] = o; });
var STATUSES = ['Postulé', 'Relancé', 'Entretien', 'Test', 'Offre', 'Refusé'];

function $(s){ return document.querySelector(s); }
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function today(){ var d = new Date(); return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2); }
function ago(d){
  if (!/^\d{4}-\d{2}-\d{2}/.test(d || '')) return d || '';
  var days = Math.floor((Date.now() - new Date(d.slice(0,10) + 'T00:00:00')) / 864e5);
  if (days <= 0) return "aujourd'hui"; if (days === 1) return 'hier';
  if (days < 30) return 'il y a ' + days + ' j'; return 'il y a ' + Math.floor(days/30) + ' mois';
}
function snap(o){ return o ? {t:o.t, c:o.c, u:o.u, l:o.l, ct:o.ct, src:o.src} : {}; }
function stateOf(id){ return S[id] ? S[id].s : ''; }

// ---------- actions with undo ----------
var LABEL = {hidden:'Offre masquée', applied:'Ajoutée à tes candidatures', saved:'Gardée pour plus tard'};
function setState(id, s){
  var prev = S[id] ? JSON.parse(JSON.stringify(S[id])) : null;
  var o = byId[id] || (S[id] && S[id].o);
  if (s === null || (S[id] && S[id].s === s && s === 'saved')) {
    delete S[id];
    toast('Remise dans « À voir »', undo);
  } else {
    var cur = S[id] || {};
    S[id] = {s:s, t:(cur.s === s ? cur.t : today()), o:snap(o), st:cur.st, note:cur.note || ''};
    if (s === 'applied' && !S[id].st) S[id].st = 'Postulé';
    toast(LABEL[s], undo);
  }
  function undo(){ if (prev) S[id] = prev; else delete S[id]; save(KEY, S); render(); }
  save(KEY, S); render();
}

var toastTimer;
function toast(msg, undo){
  var t = $('#toast'); t.querySelector('span').textContent = msg;
  var b = t.querySelector('button'); b.onclick = function(){ undo(); t.classList.remove('show'); };
  t.classList.add('show'); clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ t.classList.remove('show'); }, 5000);
}

// ---------- filters ----------
var CHIPS = [
  ['new', 'Nouveautés', function(o){ return o.n; }],
  ['vie', 'VIE', function(o){ return o.vie; }],
  ['stage', 'Stage', function(o){ return /intern|stage|stagiaire/i.test(o.ct + ' ' + o.t); }],
  ['grad', 'Graduate', function(o){ return o.grad; }],
  ['eu', 'Europe (sans visa)', function(o){ return o.reg === 'west' || o.reg === 'south'; }],
  ['sal', 'Salaire affiché', function(o){ return !!o.sal; }],
  ['top', 'Score ≥ 70', function(o){ return o.sc >= 70; }],
  ['visa', 'Visa sponsorisé', function(o){ return o.visa; }],
  ['dated', 'Date de début connue', function(o){ return !!o.st; }]
];
function matchQ(o, q){
  if (!q) return true;
  var hay = (o.t+' '+o.c+' '+o.l+' '+o.ct+' '+o.src).toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
  return q.split(/\s+/).every(function(w){ return hay.indexOf(w) >= 0; });
}
function normQ(q){ return (q || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim(); }
function sorter(a, b){
  if (UI.sort === 'recent') return (b.d || '').localeCompare(a.d || '');
  if (UI.sort === 'start') return (a.st || '9999').localeCompare(b.st || '9999') || b.sc - a.sc;
  if (UI.sort === 'new') return (b.n - a.n) || (b.sc - a.sc);
  return b.sc - a.sc;
}

// ---------- rendering ----------
function badges(o){
  var h = '';
  if (o.n) h += '<span class="badge b-new">NEW</span>';
  if (o.vie) h += '<span class="badge b-vie">VIE</span>';
  if (o.grad) h += '<span class="badge b-grad">GRAD</span>';
  if (o.visa) h += '<span class="badge b-visa" title="Hors UE — l\'offre dit sponsoriser le visa">VISA ✓</span>';
  if (!o.st) h += '<span class="badge b-nodate" title="L\'offre n\'indique pas de date de début">DATE ?</span>';
  return h;
}
function offerCard(o){
  var s = stateOf(o.id);
  var meta = [ '<b>' + esc(o.c) + '</b>' ];
  if (o.sz) meta.push(esc(o.sz) + (/^\d+$/.test(o.sz) ? ' pers.' : ''));
  if (o.l) meta.push('📍 ' + esc(o.l));
  if (o.ct) meta.push(esc(o.ct));
  if (o.st) meta.push('Début ' + esc(o.st));
  if (o.sal) meta.push('<span class="pay">💶 ' + esc(o.sal) + '</span>');
  if (o.src !== 'VIE') meta.push(esc(o.src));
  if (o.d) meta.push('<span title="' + esc(o.d) + '">' + esc(ago(o.d)) + '</span>');
  var why = (o.why || []).map(function(r){ return '<span>' + esc(r) + '</span>'; }).join('');
  return '<article class="offer" data-id="' + esc(o.id) + '">' +
    '<div class="main"><div class="line1"><span class="score ' + (o.sc >= 70 ? 's-hi' : o.sc >= 55 ? 's-mid' : '') + '" title="Score sur 100 — détail dans « Détails »">' + o.sc + '</span>' + badges(o) +
    '<a class="title" href="' + esc(o.u) + '" target="_blank" rel="noopener">' + esc(o.t) + '</a></div>' +
    '<div class="meta">' + meta.map(function(m){ return '<span>' + m + '</span>'; }).join('') + '</div>' +
    ((why || o.desc) ? '<details class="why"><summary>Détails</summary>' +
      (why ? '<p class="reasons">' + why + '</p>' : '') +
      (o.desc ? '<p>' + esc(o.desc) + '…</p>' : '') +
      '<p class="prep"><button class="btn" data-prep="1">📝 Préparer ma candidature</button></p></details>' : '') +
    '</div><div class="actions">' +
    '<button class="btn star' + (s === 'saved' ? ' on' : '') + '" data-act="saved" title="À garder (raccourci S)">' + (s === 'saved' ? '★' : '☆') + '</button>' +
    '<button class="btn primary" data-act="applied" title="Raccourci A">✓ Postulé</button>' +
    '<button class="btn" data-act="hidden" title="Raccourci X">✕ Pas intéressé</button>' +
    '</div></article>';
}

function counts(){
  var c = {todo:0, saved:0, applied:0, hidden:0};
  OFFERS.forEach(function(o){ if (!S[o.id]) c.todo++; });
  Object.keys(S).forEach(function(id){ if (c[S[id].s] !== undefined) c[S[id].s]++; });
  return c;
}

function renderTabs(){
  var c = counts();
  document.querySelectorAll('nav.tabs button').forEach(function(b){
    var k = b.dataset.tab; b.classList.toggle('on', k === UI.tab);
    var n = b.querySelector('.n'); if (n && c[k] !== undefined) n.textContent = c[k];
  });
  document.querySelectorAll('section[data-view]').forEach(function(s){
    s.classList.toggle('hidden', s.dataset.view !== UI.tab);
  });
}

function renderTodo(){
  var q = normQ(UI.q);
  var base = OFFERS.filter(function(o){ return !S[o.id] && matchQ(o, q); });
  var active = CHIPS.filter(function(c){ return UI.chips.indexOf(c[0]) >= 0; });
  var list = base.filter(function(o){ return active.every(function(c){ return c[2](o); }); }).sort(sorter);
  $('#chips').innerHTML = CHIPS.map(function(c){
    var n = base.filter(c[2]).length;
    return '<button class="chip' + (UI.chips.indexOf(c[0]) >= 0 ? ' on' : '') + '" data-chip="' + c[0] + '">' +
      c[1] + '<span class="c">' + n + '</span></button>';
  }).join('');
  $('#todo-count').textContent = list.length + ' offre' + (list.length > 1 ? 's' : '') + ' affichée' + (list.length > 1 ? 's' : '');
  $('#todo-list').innerHTML = list.length ? list.map(offerCard).join('') :
    '<div class="empty">' + (OFFERS.length ? 'Tout est trié 🎉 — aucune offre ne correspond à ces filtres.' : "Aucune offre aujourd'hui.") + '</div>';
}

function storedList(state){
  return Object.keys(S).filter(function(id){ return S[id].s === state; })
    .map(function(id){ var live = byId[id]; var r = live ? Object.assign({}, live) : Object.assign({id:id, gone:true}, S[id].o);
      r.id = id; r._s = S[id]; return r; })
    .sort(function(a, b){ return (b._s.t || '').localeCompare(a._s.t || ''); });
}

function renderSaved(){
  var list = storedList('saved');
  $('#saved-list').innerHTML = list.length ? list.map(function(o){
    return o.gone ? '<article class="offer" data-id="' + esc(o.id) + '"><div class="main"><div class="line1"><a class="title" href="' + esc(o.u) + '" target="_blank" rel="noopener">' + esc(o.t) + '</a></div><div class="meta"><span><b>' + esc(o.c) + '</b></span><span class="ko">plus en ligne ?</span></div></div><div class="actions"><button class="btn primary" data-act="applied">✓ Postulé</button><button class="btn" data-act="hidden">✕</button></div></article>'
      : offerCard(o);
  }).join('') : '<div class="empty">Clique sur ☆ pour garder une offre ici avant de postuler.</div>';
}

function renderApplied(){
  var list = storedList('applied');
  var tally = {}; STATUSES.forEach(function(s){ tally[s] = 0; });
  list.forEach(function(o){ tally[o._s.st || 'Postulé'] = (tally[o._s.st || 'Postulé'] || 0) + 1; });
  $('#pipeline').innerHTML = list.length ? STATUSES.map(function(s){
    return '<div class="st-' + s + '"><b>' + tally[s] + '</b>' + s + '</div>'; }).join('') : '';
  if (!list.length){ $('#applied-table').innerHTML = '<div class="empty">Quand tu postules, clique sur « ✓ Postulé » : l\'offre arrive ici avec la date, et tu peux suivre son statut.</div>'; return; }
  var rows = list.map(function(o){
    var st = o._s.st || 'Postulé';
    var days = Math.floor((Date.now() - new Date((o._s.t || today()) + 'T00:00:00')) / 864e5);
    var relance = (st === 'Postulé' && days >= 10) ? ' <span class="badge b-vie" title="Pas de nouvelles depuis ' + days + ' jours">À relancer</span>' : '';
    return '<tr data-id="' + esc(o.id) + '"><td>' + esc(o._s.t) + '</td>' +
      '<td><a href="' + esc(o.u) + '" target="_blank" rel="noopener">' + esc(o.t) + '</a>' + relance + '<br><span style="color:var(--muted)">' + esc(o.c) + (o.l ? ' · ' + esc(o.l) : '') + '</span></td>' +
      '<td><select data-field="st" class="st-' + st + '">' + STATUSES.map(function(s){ return '<option' + (s === st ? ' selected' : '') + '>' + s + '</option>'; }).join('') + '</select></td>' +
      '<td><input class="note" data-field="note" placeholder="Contact, date d\'entretien…" value="' + esc(o._s.note || '') + '"></td>' +
      '<td><button class="btn" data-act="reset" title="Remettre dans « À voir »">↩</button></td></tr>';
  }).join('');
  $('#applied-table').innerHTML = '<div class="tablewrap"><table class="compact"><thead><tr><th>Date</th><th>Offre</th><th>Statut</th><th>Notes</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';
}

function renderHidden(){
  var list = storedList('hidden');
  $('#hidden-table').innerHTML = list.length ? '<div class="tablewrap"><table class="compact"><thead><tr><th>Masquée le</th><th>Offre</th><th></th></tr></thead><tbody>' +
    list.map(function(o){
      return '<tr data-id="' + esc(o.id) + '"><td>' + esc(o._s.t) + '</td><td><a href="' + esc(o.u) + '" target="_blank" rel="noopener">' + esc(o.t) + '</a> <span style="color:var(--muted)">— ' + esc(o.c) + '</span></td>' +
        '<td><button class="btn" data-act="reset">Restaurer</button></td></tr>';
    }).join('') + '</tbody></table></div>' : '<div class="empty">Les offres « Pas intéressé » arrivent ici. Tu peux les restaurer à tout moment.</div>';
  $('#restore-all').classList.toggle('hidden', !list.length);
}

function render(){
  renderTabs();
  if (UI.tab === 'todo') renderTodo();
  if (UI.tab === 'saved') renderSaved();
  if (UI.tab === 'applied') renderApplied();
  if (UI.tab === 'hidden') renderHidden();
  save(UIKEY, {tab:UI.tab, chips:UI.chips, sort:UI.sort});
}

// ---------- events ----------
document.addEventListener('click', function(e){
  var tab = e.target.closest('nav.tabs button');
  if (tab){ UI.tab = tab.dataset.tab; render(); window.scrollTo(0, 0); return; }
  var chip = e.target.closest('[data-chip]');
  if (chip){ var k = chip.dataset.chip, i = UI.chips.indexOf(k);
    if (i >= 0) UI.chips.splice(i, 1); else UI.chips.push(k); render(); return; }
  var prep = e.target.closest('[data-prep]');
  if (prep){ var po = byId[prep.closest('[data-id]').dataset.id];
    var txt = 'Prépare ma candidature (CV + lettre de motivation adaptés) pour cette offre : ' + po.t + ' — ' + po.c + ' — ' + po.u;
    (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(function(){
      toast('Copié — colle-le dans Claude (projet Stage)', function(){}); },
      function(){ prompt('Copie ce texte et colle-le dans Claude :', txt); });
    return; }
  var act = e.target.closest('[data-act]');
  if (act){ var id = act.closest('[data-id]').dataset.id, a = act.dataset.act;
    setState(id, a === 'reset' ? null : a); return; }
});
document.addEventListener('change', function(e){
  var f = e.target.dataset && e.target.dataset.field; if (!f) return;
  var id = e.target.closest('[data-id]').dataset.id; if (!S[id]) return;
  S[id][f] = e.target.value; save(KEY, S);
  if (f === 'st') renderApplied();
});
$('#q').addEventListener('input', function(e){ UI.q = e.target.value; renderTodo(); });
$('#sort').value = UI.sort;
$('#sort').addEventListener('change', function(e){ UI.sort = e.target.value; render(); });
$('#restore-all').addEventListener('click', function(){
  if (!confirm('Restaurer toutes les offres masquées ?')) return;
  Object.keys(S).forEach(function(id){ if (S[id].s === 'hidden') delete S[id]; }); save(KEY, S); render();
});

// keyboard: J/K move, X hide, A applied, S save, O open, / search
var cur = -1;
function cards(){ return Array.prototype.slice.call(document.querySelectorAll('section:not(.hidden) .offer')); }
function focusCard(i){ var c = cards(); if (!c.length) return; cur = Math.max(0, Math.min(i, c.length - 1));
  c.forEach(function(x, j){ x.style.outline = j === cur ? '2px solid var(--accent)' : ''; });
  c[cur].scrollIntoView({block:'nearest'}); }
document.addEventListener('keydown', function(e){
  if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
  var k = e.key.toLowerCase(), c = cards();
  if (k === '/'){ e.preventDefault(); UI.tab = 'todo'; render(); $('#q').focus(); return; }
  if (k === 'j'){ focusCard(cur + 1); return; }
  if (k === 'k'){ focusCard(cur - 1); return; }
  if (cur < 0 || !c[cur]) return;
  var id = c[cur].dataset.id;
  if (k === 'o'){ window.open(c[cur].querySelector('a.title').href, '_blank'); return; }
  var map = {x:'hidden', a:'applied', s:'saved'};
  if (map[k]){ var keep = cur; setState(id, map[k]); focusCard(keep); }
});

// ---------- backup (move your choices between phone and PC) ----------
$('#export').addEventListener('click', function(){
  var blob = new Blob([JSON.stringify(S, null, 1)], {type:'application/json'});
  var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'suivi-candidatures-' + today() + '.json'; a.click();
});
$('#import').addEventListener('change', function(e){
  var file = e.target.files[0]; if (!file) return;
  var r = new FileReader();
  r.onload = function(){
    try { var data = JSON.parse(r.result), n = 0;
      Object.keys(data).forEach(function(id){ if (data[id] && data[id].s){ S[id] = data[id]; n++; } });
      save(KEY, S); render(); toast(n + ' éléments importés', function(){});
    } catch(err){ alert('Fichier invalide'); }
  };
  r.readAsText(file); e.target.value = '';
});

render();
})();
"""


def _snippet(text: str, n: int = 420) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:n]


def _offer_dict(o) -> dict:
    kind = (o.contract + " " + o.title).lower()
    return {
        "id": o.uid, "t": o.title, "c": o.company, "sz": o.size_label,
        "l": o.location, "ct": o.contract, "st": o.start_date, "src": o.source,
        "d": o.date, "u": o.url, "sc": o.score, "n": bool(o.is_new),
        "vie": o.source == "VIE" or o.contract == "VIE",
        "grad": "graduate" in kind or "trainee" in kind,
        "visa": bool(getattr(o, "visa_ok", False)),
        "reg": getattr(o, "region", ""),
        "sal": getattr(o, "salary_label", ""),
        "why": list(o.reasons or []), "desc": _snippet(o.description),
    }


def _grad_table(programs) -> str:
    if not programs:
        return '<div class="empty">Aucun programme listé (grad_programs.yaml).</div>'
    this_month = datetime.now().month
    rows = []
    # programs you can actually join (no visa sponsorship needed) first
    programs = sorted(programs, key=lambda p: bool(p.get("needs_sponsorship")))
    for p in programs:
        badge = ('<span class="badge b-new">OUVRE CE MOIS-CI</span> '
                 if p.get("opens_month") == this_month else "")
        style = ' style="opacity:.5"' if p.get("needs_sponsorship") else ""
        rows.append(
            f"<tr{style}>"
            f'<td>{badge}<a href="{html.escape(p.get("url") or "")}" target="_blank" rel="noopener">'
            f'{html.escape(p.get("program") or "")}</a><br>'
            f'<span style="color:var(--muted)">{html.escape(p.get("company") or "")}</span></td>'
            f'<td>{html.escape(p.get("window") or MONTH_NAMES[p.get("opens_month") or 0])}</td>'
            f'<td>{html.escape(p.get("region") or "")}</td>'
            f'<td>{html.escape(p.get("visa") or "")}</td>'
            f'<td>{html.escape(p.get("fit") or "")}</td>'
            "</tr>"
        )
    return f"""
<p class="sub">Les fenêtres de candidature sont des tendances des années précédentes — vérifie sur la page.
Rappel par notification le 1er du mois d'ouverture. Les lignes grisées demandent un visa rarement sponsorisé (pas de rappel).</p>
<div class="tablewrap"><table class="compact">
<thead><tr><th>Programme</th><th>Candidatures</th><th>Région</th><th>Visa</th><th>Pourquoi toi</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>"""


def _drops_table(drops) -> str:
    if not drops:
        return ""
    rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>"
                   for k, v in sorted(drops.items(), key=lambda kv: -kv[1]))
    return f"""
<h3 style="margin:22px 0 8px">Offres écartées par tes filtres</h3>
<div class="tablewrap"><table class="compact">
<thead><tr><th>Motif</th><th>Offres</th></tr></thead><tbody>{rows}</tbody></table></div>"""


def _health_table(health, kept_by_source) -> str:
    """For each source: offers returned today and how many survived your
    filters — a source stuck at 0 is broken or blocked."""
    if not health:
        return '<div class="empty">Pas d\'information sur les sources.</div>'
    rows = []
    for name, label, fetched, error in health:
        if fetched is None:
            status = f'<span class="ko">ignorée — {html.escape(error)}</span>'
        elif fetched == 0:
            status = '<span class="ko">0 résultat — bloquée ou mal configurée ?</span>'
        else:
            status = '<span class="ok">OK</span>'
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{'' if fetched is None else fetched}</td>"
                    f"<td>{kept_by_source.get(label, 0)}</td><td>{status}</td></tr>")
    return f"""
<p class="sub">Offres récupérées aujourd'hui par source, et combien passent tes filtres.</p>
<div class="tablewrap"><table class="compact">
<thead><tr><th>Source</th><th>Récupérées</th><th>Gardées</th><th>État</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>"""


def write_reports(offers, programs=None, health=None, kept_by_source=None, drops=None) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%d/%m/%Y à %H:%M")
    n_new = sum(1 for o in offers if o.is_new)
    data = json.dumps([_offer_dict(o) for o in offers], ensure_ascii=False)
    data = data.replace("</", "<\\/")   # keep the JSON safe inside <script>

    page = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Offres — {stamp}</title><style>{CSS}</style></head>
<body><div class="wrap">
<header>
  <h1>Mes offres</h1>
  <p class="sub">{len(offers)} offres correspondent à ton profil, dont {n_new} nouvelles — mis à jour le {stamp}.
  Classées de la meilleure à la moins bonne (score sur 100).</p>
</header>
<nav class="tabs">
  <button data-tab="todo">À voir<span class="n"></span></button>
  <button data-tab="saved">★ Gardées<span class="n"></span></button>
  <button data-tab="applied">✓ Candidatures<span class="n"></span></button>
  <button data-tab="hidden">Masquées<span class="n"></span></button>
  <button data-tab="programs">Graduate programs</button>
  <button data-tab="sources">Sources</button>
</nav>

<section data-view="todo">
  <div class="toolbar">
    <input id="q" type="search" placeholder="Rechercher (titre, entreprise, ville…)  —  touche /" aria-label="Rechercher">
    <select id="sort" aria-label="Trier">
      <option value="score">Tri : meilleures offres</option>
      <option value="new">Tri : nouveautés d'abord</option>
      <option value="recent">Tri : plus récentes</option>
      <option value="start">Tri : date de début</option>
    </select>
  </div>
  <div class="chips" id="chips"></div>
  <p class="count" id="todo-count"></p>
  <div class="list" id="todo-list"></div>
</section>

<section data-view="saved" class="hidden">
  <p class="sub">Offres mises de côté avec ☆, en attendant de postuler.</p>
  <div class="list" id="saved-list"></div>
</section>

<section data-view="applied" class="hidden">
  <div class="pipeline" id="pipeline"></div>
  <div id="applied-table"></div>
</section>

<section data-view="hidden" class="hidden">
  <div class="toolbar"><button class="btn" id="restore-all">Tout restaurer</button></div>
  <div id="hidden-table"></div>
</section>

<section data-view="programs" class="hidden">{_grad_table(programs)}</section>
<section data-view="sources" class="hidden">{_health_table(health, kept_by_source or {})}{_drops_table(drops)}</section>

<footer>
  <span>Tes choix sont enregistrés dans ce navigateur. Pour les passer sur un autre appareil :</span>
  <button class="btn" id="export">Exporter</button>
  <label class="btn">Importer<input id="import" type="file" accept="application/json" hidden></label>
  <span class="hide-sm">· Clavier : <span class="kbd">J</span>/<span class="kbd">K</span> naviguer,
  <span class="kbd">A</span> postulé, <span class="kbd">X</span> pas intéressé, <span class="kbd">S</span> garder,
  <span class="kbd">O</span> ouvrir, <span class="kbd">/</span> rechercher</span>
</footer>
</div>
<div id="toast" role="status"><span></span><button>Annuler</button></div>
<script type="application/json" id="data-offers">{data}</script>
<script>{JS}</script>
</body></html>"""

    html_path = OUT_DIR / "index.html"
    html_path.write_text(page, encoding="utf-8")

    with open(OUT_DIR / "offers.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["New", "Score", "Title", "Company", "Size", "Location", "Contract", "Start", "Source", "Date", "Link"])
        for o in offers:
            w.writerow(["yes" if o.is_new else "", o.score, o.title, o.company, o.size_label,
                        o.location, o.contract, o.start_date, o.source, o.date, o.url])

    return html_path


def write_new_offers_summary(offers, programs=None, max_items: int = 30) -> int:
    """Write docs/new_offers.md + docs/new_count.txt (used by the daily
    GitHub notification). Returns the number of notification items."""
    new = [o for o in offers if o.is_new]
    today = datetime.now()
    # on the 1st of a month, remind about grad programs opening that month
    reminders = [p for p in (programs or [])
                 if p.get("opens_month") == today.month and today.day == 1
                 and not p.get("needs_sponsorship")]

    lines = []
    if new:
        lines += [f"**{len(new)} new offer(s) match your profile today.**", ""]
        for o in new[:max_items]:
            lines.append(f"- [{o.title}]({o.url}) — {o.company} — {o.location} — {o.contract}")
        if len(new) > max_items:
            lines.append(f"- …and {len(new) - max_items} more on the dashboard.")
    if reminders:
        lines += ["", "**📅 Graduate program applications likely opening this month — go check:**", ""]
        for p in reminders:
            lines.append(f"- [{p.get('company')} — {p.get('program')}]({p.get('url')}) ({p.get('window')})")
    lines += ["", "Full list: see your dashboard (GitHub Pages link in the README)."]
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "new_offers.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT_DIR / "new_count.txt").write_text(str(len(new) + len(reminders)), encoding="utf-8")
    return len(new) + len(reminders)
