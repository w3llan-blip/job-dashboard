"""Fetch offers from companies' public Lever job boards.

Lever provides an official, public, read-only postings API:
https://api.lever.co/v0/postings/<company>
"""
import requests

from ..models import Offer

API = "https://api.lever.co/v0/postings/{}?mode=json"
UA = "job-dashboard (personal job search tool)"


def fetch(config: dict) -> list[Offer]:
    companies = (config.get("companies") or {}).get("lever") or []
    offers: list[Offer] = []
    for slug in companies:
        try:
            resp = requests.get(API.format(slug), timeout=20, headers={"User-Agent": UA})
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            jobs = resp.json()
            if not isinstance(jobs, list):
                continue
        except requests.RequestException:
            continue
        for j in jobs:
            cats = j.get("categories") or {}
            commitment = (cats.get("commitment") or "").strip()
            offers.append(Offer(
                uid=f"lever:{slug}:{j.get('id')}",
                source="Lever",
                company=slug.replace("-", " ").title(),
                title=(j.get("text") or "").strip(),
                location=(cats.get("location") or "").strip(),
                url=j.get("hostedUrl") or "",
                description=(j.get("descriptionPlain") or "")[:1500],
                contract=commitment,
            ))
    return offers
