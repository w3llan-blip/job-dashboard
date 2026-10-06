"""Fetch offers from the official France Travail API ("Offres d'emploi v2").

Free, official and legal, but it needs a personal API key:
  1. create an account on https://francetravail.io
  2. create an application and subscribe it to the "Offres d'emploi" API
  3. put the client id / secret in two GitHub secrets named
     FT_CLIENT_ID and FT_CLIENT_SECRET (or in environment variables on
     your PC). Without them this source is simply skipped.
"""
from __future__ import annotations

import os
import re
import time

import requests

from ..models import Offer

TOKEN_URL = ("https://entreprise.francetravail.fr/connexion/oauth2/access_token"
             "?realm=%2Fpartenaire")
SEARCH = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
DETAIL_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{}"


def _token(cid: str, secret: str) -> str:
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials", "client_id": cid,
        "client_secret": secret, "scope": "api_offresdemploiv2 o2dsoffre",
    }, timeout=20)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headcount(label: str) -> int | None:
    """'250 à 499 salariés' -> 250 (lower bound)."""
    m = re.search(r"(\d[\d\s]*)", label or "")
    return int(m.group(1).replace(" ", "")) if m else None


def fetch(config: dict) -> list[Offer]:
    cid = os.environ.get("FT_CLIENT_ID")
    secret = os.environ.get("FT_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("no API key (FT_CLIENT_ID / FT_CLIENT_SECRET not set)")

    cfg = config.get("france_travail") or {}
    queries = cfg.get("queries") or []
    min_emp = int((config.get("company_size") or {}).get("min_employees") or 0)
    token = _token(cid, secret)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    offers: dict[str, Offer] = {}
    for q in queries:
        params = {"motsCles": q, "range": "0-149"}
        if cfg.get("cadre_only", True):
            params["qualification"] = "9"     # cadre
        resp = requests.get(SEARCH, params=params, headers=headers, timeout=30)
        if resp.status_code == 204:           # no result
            continue
        resp.raise_for_status()
        for r in resp.json().get("resultats") or []:
            oid = r.get("id")
            if not oid or f"ft:{oid}" in offers:
                continue
            size_label = r.get("trancheEffectifEtab") or ""
            employees = _headcount(size_label)
            if employees is not None and employees < min_emp:
                continue
            company = ((r.get("entreprise") or {}).get("nom") or "").strip()
            offers[f"ft:{oid}"] = Offer(
                uid=f"ft:{oid}",
                source="France Travail",
                company=company or "(entreprise non communiquée)",
                title=(r.get("intitule") or "").strip(),
                location=((r.get("lieuTravail") or {}).get("libelle") or "").strip(),
                url=((r.get("origineOffre") or {}).get("urlOrigine")
                     or DETAIL_URL.format(oid)),
                description=(r.get("description") or "")[:4000],
                contract=r.get("typeContratLibelle") or r.get("typeContrat") or "",
                date=(r.get("dateCreation") or "")[:10],
                employees=employees,
                size_label=size_label.replace(" salariés", ""),
            )
        time.sleep(0.2)   # API allows a few calls per second
    return list(offers.values())
