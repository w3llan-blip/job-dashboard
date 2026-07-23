"""Fetch offers from LinkedIn's public (logged-out) job search.

Uses the same "guest" endpoints a browser hits when browsing jobs
without an account — no login, no cookies, nothing tied to a person.
LinkedIn may rate-limit these requests; every failure is silently
skipped so the rest of the run is never affected.

To keep requests low we:
- only ask for offers posted in the last 7 days
- pre-filter by title before fetching any job description
- pause between requests
"""
import html as htmllib
import re
import time

import requests

from ..models import Offer

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
LAST_7_DAYS = "r604800"
PAGES_PER_QUERY = 2      # 25 results per page
MAX_DETAIL_FETCHES = 40  # description downloads per run
PAUSE = 1.5              # seconds between requests

CARD_RE = re.compile(
    r'base-card__full-link[^"]*"\s+href="([^"]+)".*?'
    r'base-search-card__title[^>]*>\s*(.*?)\s*</h3>.*?'
    r'base-search-card__subtitle[^>]*>\s*(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?\s*</h4>.*?'
    r'job-search-card__location[^>]*>\s*(.*?)\s*</span>',
    re.S,
)
DESC_RE = re.compile(r'show-more-less-html__markup[^>]*>(.*?)</div>', re.S)


def _strip_html(text: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def _title_prefilter(title: str, config: dict) -> bool:
    """Cheap check with the user's keywords before spending a request."""
    kw = config.get("keywords") or {}
    t = " " + title.lower() + " "
    if any(x.lower() in t for x in kw.get("exclude") or []):
        return False
    return any(w.lower() in t for w in kw.get("include") or [])


def fetch(config: dict) -> list[Offer]:
    queries = (config.get("linkedin") or {}).get("queries") or []
    session = requests.Session()
    session.headers["User-Agent"] = UA

    found: dict[str, Offer] = {}
    for q in queries:
        for page in range(PAGES_PER_QUERY):
            try:
                resp = session.get(SEARCH, params={
                    "keywords": q.get("keywords") or "",
                    "location": q.get("location") or "",
                    "f_TPR": LAST_7_DAYS,
                    "start": page * 25,
                }, timeout=20)
                if resp.status_code != 200 or not resp.text.strip():
                    break  # rate-limited or no more results
            except requests.RequestException:
                break
            cards = CARD_RE.findall(resp.text)
            if not cards:
                break
            for url, title, company, location in cards:
                m = re.search(r"(\d{8,})", url.split("?")[0])
                if not m:
                    continue
                uid = f"li:{m.group(1)}"
                if uid in found:
                    continue
                found[uid] = Offer(
                    uid=uid,
                    source="LinkedIn",
                    company=_strip_html(company),
                    title=_strip_html(title),
                    location=_strip_html(location),
                    url=url.split("?")[0],
                )
            time.sleep(PAUSE)

    # fetch descriptions only for title-matching offers (start-date +
    # disqualifier filters need the text)
    fetched = 0
    for offer in found.values():
        if fetched >= MAX_DETAIL_FETCHES:
            break
        if not _title_prefilter(offer.title, config):
            continue
        job_id = offer.uid.split(":")[1]
        try:
            resp = session.get(DETAIL.format(job_id), timeout=20)
            if resp.status_code == 200:
                m = DESC_RE.search(resp.text)
                if m:
                    offer.description = _strip_html(m.group(1))[:4000]
        except requests.RequestException:
            pass
        fetched += 1
        time.sleep(PAUSE)

    return list(found.values())
