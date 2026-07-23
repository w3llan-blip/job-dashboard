"""Write the results as a web page with per-column filters (and a CSV backup).

Output goes to docs/ so GitHub Pages can serve it at a public URL.
"""
import csv
import html
from datetime import datetime
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "docs"

CSS = """
*{box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;margin:16px;background:#f7f8fa;color:#1c2733}
h1{font-size:22px;margin:4px 0} .sub{color:#5b6875;margin:0 0 14px}
.toolbar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.toolbar label{font-size:14px;display:flex;gap:6px;align-items:center}
.tablewrap{overflow-x:auto;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
table{border-collapse:collapse;width:100%;min-width:860px}
th,td{padding:8px 10px;text-align:left;font-size:14px;border-bottom:1px solid #eef1f4}
thead th{background:#0f2438;color:#fff;position:sticky;top:0;white-space:nowrap}
thead input{width:100%;min-width:70px;padding:5px 7px;font-size:13px;border:1px solid #cbd4dc;border-radius:6px}
tr:hover td{background:#f0f6ff}
a{color:#0b5fff;text-decoration:none} a:hover{text-decoration:underline}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.new{background:#e1f7e7;color:#137333}
.vie{background:#fff3d6;color:#8a6100}
.score{font-weight:700}
.count{font-size:13px;color:#5b6875}
"""

JS = """
var inputs = document.querySelectorAll('thead input[data-col]');
var newOnly = document.getElementById('newonly');
function applyFilters(){
  var active = [];
  inputs.forEach(function(inp){
    var v = inp.value.trim().toLowerCase();
    if (v) active.push({col: +inp.dataset.col, q: v});
  });
  var shown = 0;
  document.querySelectorAll('tbody tr').forEach(function(tr){
    var ok = true;
    if (newOnly.checked && tr.dataset.new !== '1') ok = false;
    for (var i = 0; ok && i < active.length; i++){
      var cell = tr.cells[active[i].col];
      if (cell.textContent.toLowerCase().indexOf(active[i].q) < 0) ok = false;
    }
    tr.style.display = ok ? '' : 'none';
    if (ok) shown++;
  });
  document.getElementById('count').textContent = shown + ' offers shown';
}
inputs.forEach(function(i){ i.addEventListener('input', applyFilters); });
newOnly.addEventListener('change', applyFilters);
applyFilters();
"""

COLUMNS = ["", "Score", "Offer", "Company", "Location", "Contract", "Start", "Source", "Date"]


MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def _grad_table(programs) -> str:
    if not programs:
        return ""
    this_month = datetime.now().month
    rows = []
    for p in programs:
        badge = ('<span class="badge new">OPENING NOW</span> '
                 if p.get("opens_month") == this_month else "")
        rows.append(
            "<tr>"
            f'<td>{badge}<a href="{html.escape(p.get("url") or "")}" target="_blank" rel="noopener">'
            f'{html.escape(p.get("program") or "")}</a></td>'
            f'<td>{html.escape(p.get("company") or "")}</td>'
            f'<td>{html.escape(p.get("window") or MONTH_NAMES[p.get("opens_month") or 0])}</td>'
            f'<td>{html.escape(p.get("region") or "")}</td>'
            f'<td>{html.escape(p.get("fit") or "")}</td>'
            "</tr>"
        )
    return f"""
<h2 style="margin-top:28px">Graduate programs to track (2027 intake)</h2>
<p class="sub">Application windows are typical patterns — verify on the page.
You'll get a reminder notification on the 1st of each opening month.</p>
<div class="tablewrap">
<table>
<thead><tr><th>Program</th><th>Company</th><th>Applications</th><th>Region</th><th>Why you</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</div>"""


def write_reports(offers, programs=None) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    n_new = sum(1 for o in offers if o.is_new)

    rows = []
    for o in offers:
        badges = ""
        if o.is_new:
            badges += '<span class="badge new">NEW</span> '
        if o.source == "VIE":
            badges += '<span class="badge vie">VIE</span>'
        rows.append(
            f'<tr data-new="{1 if o.is_new else 0}">'
            f"<td>{badges}</td>"
            f'<td class="score">{o.score}</td>'
            f'<td><a href="{html.escape(o.url)}" target="_blank" rel="noopener">{html.escape(o.title)}</a></td>'
            f"<td>{html.escape(o.company)}</td>"
            f"<td>{html.escape(o.location)}</td>"
            f"<td>{html.escape(o.contract)}</td>"
            f"<td>{html.escape(o.start_date or '—')}</td>"
            f"<td>{html.escape(o.source)}</td>"
            f"<td>{html.escape(o.date)}</td>"
            "</tr>"
        )

    # filter row: a search box under each column header (except badges/score)
    filter_cells = []
    for i, name in enumerate(COLUMNS):
        if i in (0, 1):
            filter_cells.append("<th></th>")
        else:
            filter_cells.append(
                f'<th><input data-col="{i}" type="search" placeholder="filter…" '
                f'aria-label="Filter by {name}"></th>'
            )

    header_cells = "".join(f"<th>{c}</th>" for c in COLUMNS)

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job offers — {stamp}</title><style>{CSS}</style></head>
<body>
<h1>Your job matches</h1>
<p class="sub">{len(offers)} matching offers ({n_new} new since last run) — updated {stamp}.
Sorted: new first, then best score. Filters combine (AND).</p>
<div class="toolbar">
  <label><input type="checkbox" id="newonly"> New offers only</label>
  <span class="count" id="count"></span>
</div>
<div class="tablewrap">
<table>
<thead>
<tr>{header_cells}</tr>
<tr>{''.join(filter_cells)}</tr>
</thead>
<tbody>{''.join(rows)}</tbody>
</table>
</div>
{_grad_table(programs)}
<script>{JS}</script>
</body></html>"""

    html_path = OUT_DIR / "index.html"
    html_path.write_text(page, encoding="utf-8")

    with open(OUT_DIR / "offers.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["New", "Score", "Title", "Company", "Location", "Contract", "Start", "Source", "Date", "Link"])
        for o in offers:
            w.writerow(["yes" if o.is_new else "", o.score, o.title, o.company,
                        o.location, o.contract, o.start_date, o.source, o.date, o.url])

    return html_path


def write_new_offers_summary(offers, programs=None, max_items: int = 30) -> int:
    """Write docs/new_offers.md + docs/new_count.txt (used by the daily
    GitHub notification). Returns the number of notification items."""
    new = [o for o in offers if o.is_new]
    today = datetime.now()
    # on the 1st of a month, remind about grad programs opening that month
    reminders = [p for p in (programs or [])
                 if p.get("opens_month") == today.month and today.day == 1]

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
