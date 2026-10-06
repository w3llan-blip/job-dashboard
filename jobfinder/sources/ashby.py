"""Fetch offers from companies' public Ashby job boards.

Many scale-ups moved from Greenhouse/Lever to Ashby. Ashby offers an
official public postings API: https://api.ashbyhq.com/posting-api/job-board/<slug>
The slug is the last part of the company's board address
(https://jobs.ashbyhq.com/<slug>).
"""
import requests

from ..models import Offer

API = "https://api.ashbyhq.com/posting-api/job-board/{}"
UA = "job-dashboard (personal job search tool)"


def fetch(config: dict) -> list[Offer]:
    companies = (config.get("companies") or {}).get("ashby") or []
    offers: list[Offer] = []
    for slug in companies:
        try:
            resp = requests.get(API.format(slug), timeout=20, headers={"User-Agent": UA})
            if resp.status_code == 404:
                print(f"[Ashby {slug}: not found]", end=" ")
                continue
            resp.raise_for_status()
            jobs = resp.json().get("jobs") or []
        except (requests.RequestException, ValueError):
            continue
        for j in jobs:
            if j.get("isListed") is False:
                continue
            offers.append(Offer(
                uid=f"ashby:{slug}:{j.get('id')}",
                source="Ashby",
                company=slug.replace("-", " ").title(),
                title=(j.get("title") or "").strip(),
                location=(j.get("location") or "").strip(),
                url=j.get("jobUrl") or "",
                description=(j.get("descriptionPlain") or "")[:3000],
                contract=(j.get("employmentType") or "").replace("FullTime", "Full-time"),
                date=(j.get("publishedAt") or "")[:10],
            ))
    return offers
