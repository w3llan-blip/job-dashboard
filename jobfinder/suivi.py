"""Copy a summary of Saliou's application statuses to suivi_candidatures.json,
so Claude (who cannot open the private sync gist) can read them.

Run by the daily workflow after the search: it reads the sync gist (its id
is the SYNC_GIST_ID secret; a secret gist can be read with its id alone),
then writes, for every « star » offer (docs/star.json), the status that the
« ⭐ Star » tab shows, and the list of offers marked as applied.
Only titles, companies, statuses and dates are copied: never notes.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "suivi_candidatures.json"
STARS = ROOT / "docs" / "star.json"
FILE = "job-dashboard-choices.json"
APPLIED = {"Postulé", "Relancé", "Entretien", "Test", "Offre", "Refusé"}


def _fetch(gist_id: str) -> dict:
    last = None
    for attempt in range(3):
        try:
            r = requests.get(f"https://api.github.com/gists/{gist_id}", timeout=30,
                             headers={"Accept": "application/vnd.github+json"})
            if r.ok:
                f = (r.json().get("files") or {}).get(FILE) or {}
                content = f.get("content") or ""
                if f.get("truncated") and f.get("raw_url"):
                    content = requests.get(f["raw_url"], timeout=30).text
                return json.loads(content or "{}")
            last = f"HTTP {r.status_code}"
        except (requests.RequestException, ValueError) as exc:
            last = str(exc)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"gist illisible ({last})")


def _date(entry: dict) -> str:
    m = entry.get("m")
    if m:
        return datetime.fromtimestamp(m / 1000, timezone.utc).date().isoformat()
    return entry.get("t") or ""


def star_status(x: dict, S: dict) -> tuple[str, str, str]:
    """(status, since, set by) — same rule as the page."""
    e = S.get("star:" + x["id"])
    if e and e.get("st"):
        return e["st"], _date(e), "Saliou"
    d = S.get(x.get("did") or "")
    if d and d.get("s") == "applied":
        return d.get("st") or "Postulé", _date(d), "Saliou"
    if d and d.get("s") == "hidden":
        return "Pas pour moi", _date(d), "Saliou"
    return x.get("st0") or "À postuler", "", "Claude (par défaut)"


def main() -> int:
    gist_id = os.environ.get("SYNC_GIST_ID", "").strip()
    if not gist_id:
        print("SYNC_GIST_ID not set: statuses not exported")
        return 0
    try:
        data = _fetch(gist_id)
    except RuntimeError as exc:   # never break the daily run for this
        print(f"Statuses not exported: {exc}")
        return 0
    S = data.get("S") or {}
    stars = json.loads(STARS.read_text(encoding="utf-8")) if STARS.exists() else []

    star_rows = []
    for x in stars:
        st, since, who = star_status(x, S)
        star_rows.append({"id": x["id"], "entreprise": x.get("c"), "poste": x.get("t"),
                          "statut": st, "depuis": since, "par": who})
    applied = []
    for oid, e in S.items():
        if e.get("s") != "applied" or (e.get("st") or "Postulé") not in APPLIED:
            continue
        o = e.get("o") or {}
        applied.append({"id": oid, "entreprise": o.get("c"), "poste": o.get("t"), "lien": o.get("u"),
                        "statut": e.get("st") or "Postulé", "date": e.get("t") or ""})
    applied.sort(key=lambda a: a["date"], reverse=True)

    out = {"maj": datetime.now(timezone.utc).isoformat(timespec="minutes"),
           "star": star_rows, "candidatures": applied}
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    new = json.dumps(out, ensure_ascii=False, indent=1)
    # rewrite only when something changed (not just the time stamp)
    if old:
        try:
            prev = json.loads(old)
            prev.pop("maj", None)
            cur = dict(out)
            cur.pop("maj")
            if prev == cur:
                print("Statuses unchanged")
                return 0
        except ValueError:
            pass
    OUT.write_text(new, encoding="utf-8")
    print(f"Statuses exported: {len(star_rows)} star offers, {len(applied)} applications")
    return 0


if __name__ == "__main__":
    sys.exit(main())
