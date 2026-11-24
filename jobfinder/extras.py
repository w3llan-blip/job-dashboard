"""Offers curated by hand, outside the automatic sources.

- manual_offers.yaml: offers found by hand (e.g. LinkedIn Premium). They
  join the normal list ("À voir") without going through the filters,
  unless the same offer is already there.
- star_offers.yaml: the "À postuler" picks of the every-3-days watch,
  shown in their own tab with an application status.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import yaml

from .dedup import offer_key
from .models import Offer

ROOT = Path(__file__).resolve().parent.parent
MANUAL_PATH = ROOT / "manual_offers.yaml"
STAR_PATH = ROOT / "star_offers.yaml"
KEEP_DAYS = 45   # a manual offer stays this long unless told otherwise


def _load(path: Path) -> list:
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def _day(v):
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except (TypeError, ValueError):
        return None


def norm_url(u: str) -> str:
    return (u or "").split("#")[0].split("?")[0].rstrip("/").lower()


def manual_offers(today: date | None = None) -> list[Offer]:
    """Offers of manual_offers.yaml that are still current."""
    today = today or date.today()
    out = []
    for e in _load(MANUAL_PATH):
        if not (e.get("entreprise") and e.get("poste") and e.get("lien")):
            continue
        added = _day(e.get("ajoutee")) or today
        until = _day(e.get("jusqu_au")) or added + timedelta(days=KEEP_DAYS)
        deadline = _day(e.get("date_limite"))
        if deadline and deadline < until:
            until = deadline
        if until < today:
            continue
        reasons = ["ajoutée à la main (" + added.strftime("%d/%m") + ")"]
        if e.get("pourquoi"):
            reasons.append(str(e["pourquoi"]))
        if e.get("a_verifier"):
            reasons.append("À vérifier : " + str(e["a_verifier"]))
        if deadline:
            reasons.append("date limite : " + deadline.strftime("%d/%m/%Y"))
        slug = re.sub(r"[^a-z0-9]+", "-", (e["entreprise"] + " " + e["poste"]).lower()).strip("-")[:60]
        o = Offer(
            uid="main:" + slug, source="Ajout manuel", company=str(e["entreprise"]),
            title=str(e["poste"]), location=str(e.get("lieu") or ""), url=str(e["lien"]),
            description=str(e.get("pourquoi") or ""), contract=str(e.get("contrat") or "Stage"),
            date=added.isoformat(), start_date=str(e.get("debut") or ""),
            score=int(e.get("score") or 75), region="west",
        )
        o.reasons = reasons
        o.manual = True
        out.append(o)
    return out


def add_manual(matches: list[Offer], manual: list[Offer]) -> int:
    """Append the manual offers not already in the list; return how many."""
    keys = {offer_key(o) for o in matches}
    urls = {norm_url(o.url) for o in matches}
    n = 0
    for o in manual:
        if offer_key(o) in keys or norm_url(o.url) in urls:
            continue
        matches.append(o)
        n += 1
    matches.sort(key=lambda o: -o.score)
    return n


def star_offers(matches: list[Offer]) -> list[dict]:
    """star_offers.yaml as compact dicts for the page; `did` is the id of
    the same offer in today's list, so a status set there is seen too."""
    by_url = {norm_url(o.url): o.uid for o in matches}
    out = []
    for e in _load(STAR_PATH):
        if not e.get("id"):
            continue
        out.append({
            "id": str(e["id"]), "a": str(e.get("ajoutee") or ""), "src": str(e.get("source") or ""),
            "c": str(e.get("entreprise") or ""), "t": str(e.get("poste") or ""),
            "l": str(e.get("lieu") or ""), "u": str(e.get("lien") or ""),
            "why": str(e.get("pourquoi") or ""), "chk": str(e.get("a_verifier") or ""),
            "st0": str(e.get("statut") or "À postuler"), "dos": str(e.get("dossier") or ""),
            "dl": str(e.get("date_limite") or ""), "deb": str(e.get("debut") or ""),
            "did": by_url.get(norm_url(e.get("lien") or ""), ""),
        })
    return out
