"""Fetch offers from companies' public Greenhouse job boards.

Greenhouse provides an official, public, read-only API for every
company board it hosts: https://boards-api.greenhouse.io
"""
import requests

from ..models import Offer

API = "https://boards-api.greenhouse.io/v1/boards/{}/jobs"
UA = "job-dashboard (personal job search tool)"


def fetch(config: dict) -> list[Offer]:
    companies = (config.get("companies") or {}).get("greenhouse") or []
    offers: list[Offer] = []
    for slug in companies:
        try:
            resp = requests.get(API.format(slug), timeout=20, headers={"User-Agent": UA})
            if resp.status_code == 404:
                continue  # company not on Greenhouse (or renamed slug)
            resp.raise_for_status()
            jobs = resp.json().get("jobs") or []
        except requests.RequestException:
            continue  # skip unreachable boards, never fail the whole run
        for j in jobs:
            offers.append(Offer(
                uid=f"gh:{slug}:{j.get('id')}",
                source="Greenhouse",
                company=slug.replace("-", " ").title(),
                title=(j.get("title") or "").strip(),
                location=((j.get("location") or {}).get("name") or "").strip(),
                url=j.get("absolute_url") or "",
                date=(j.get("updated_at") or "")[:10],
            ))
    return offers
