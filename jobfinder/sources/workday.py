"""Fetch offers from large companies' Workday career sites.

Most big groups (Sanofi, Airbus, Michelin, Pernod Ricard...) publish
their jobs on Workday ("xxx.wd3.myworkdayjobs.com/SiteName"). Those
sites load their job list from a public JSON endpoint; we call the same
endpoint with the search words from config.yaml. Read-only, no login.

To add a company: open its job site, copy the address up to the site
name, e.g. https://sanofi.wd3.myworkdayjobs.com/SanofiCareers
and add it under `workday:` in config.yaml.
"""
import re
import time
from urllib.parse import urlparse

import requests

from ..models import Offer

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAGE = 20          # Workday's maximum page size
MAX_PER_SEARCH = 60
MAX_DETAILS = 300  # job pages downloaded per run (description + country)


def _parse(url: str):
    """https://sanofi.wd3.myworkdayjobs.com/en-US/SanofiCareers -> (host, tenant, site)."""
    u = urlparse(url.strip())
    parts = [p for p in u.path.split("/") if p]
    parts = [p for p in parts if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]  # drop locale
    if not parts:
        raise ValueError(f"no site name in {url}")
    return u.netloc, u.netloc.split(".")[0], parts[0]


def _posted(text: str) -> str:
    """'Posted Today' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago' -> ISO date."""
    t = (text or "").lower()
    days = None
    if "today" in t:
        days = 0
    elif "yesterday" in t:
        days = 1
    else:
        m = re.search(r"(\d+)\+?\s*days?", t)
        if m:
            days = int(m.group(1))
    if days is None:
        return (text or "").replace("Posted ", "").strip()
    from datetime import date, timedelta
    return (date.today() - timedelta(days=days)).isoformat()


def _strip_html(text: str) -> str:
    import html as htmllib
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def _title_ok(title: str, config: dict) -> bool:
    """Cheap keyword check before downloading a job page."""
    kw = config.get("keywords") or {}
    t = " " + title.lower() + " "
    if any(re.search(r"\b" + re.escape(x.lower()) + r"\b", t) for x in kw.get("exclude") or []):
        return False
    return any(w.lower() in t for w in kw.get("include") or []) or "vie" in t


def _find(obj, key):
    """First value of `key` anywhere in a nested JSON object."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find(v, key)
            if r is not None:
                return r
    return None


def _details(session, offers, config):
    """Download description + country for offers whose title looks right."""
    done = 0
    for o in offers:
        if done >= MAX_DETAILS or not _title_ok(o.title, config):
            continue
        host, tenant, site, path = o._wd
        try:
            r = session.get(f"https://{host}/wday/cxs/{tenant}/{site}{path}", timeout=20)
            r.raise_for_status()
            info = r.json().get("jobPostingInfo") or {}
        except (requests.RequestException, ValueError):
            continue
        done += 1
        o.description = _strip_html(info.get("jobDescription") or "")[:4000]
        country = _find(info, "country")
        if isinstance(country, dict):
            country = country.get("descriptor")
        if isinstance(country, str) and country and country.lower() not in o.location.lower():
            o.location = f"{o.location}, {country}" if o.location else country
        if info.get("location") and "location" in o.location.lower():
            o.location = info["location"] + (f", {country}" if isinstance(country, str) else "")
        time.sleep(0.2)


def fetch(config: dict) -> list[Offer]:
    sites = config.get("workday") or []
    words = (config.get("workday_search") or [""])
    offers: dict[str, Offer] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json",
                            "Content-Type": "application/json"})
    for entry in sites:
        name, url = entry.get("name"), entry.get("url")
        try:
            host, tenant, site = _parse(url)
        except ValueError:
            continue
        api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        found = 0
        for word in words:
            offset, total = 0, None
            while offset < MAX_PER_SEARCH:
                try:
                    resp = session.post(api, json={"appliedFacets": {}, "limit": PAGE,
                                                   "offset": offset, "searchText": word},
                                        timeout=20)
                    resp.raise_for_status()
                    data = resp.json()
                except (requests.RequestException, ValueError):
                    break
                if total is None:      # Workday only sends the total on page 1
                    total = data.get("total") or 0
                jobs = data.get("jobPostings") or []
                for j in jobs:
                    path = j.get("externalPath") or ""
                    uid = f"wd:{tenant}:{path}"
                    if not path or uid in offers:
                        continue
                    offers[uid] = Offer(
                        uid=uid,
                        source="Workday",
                        company=name or tenant.title(),
                        title=(j.get("title") or "").strip(),
                        location=(j.get("locationsText") or "").strip(),
                        url=f"https://{host}/{site}{path}",
                        date=_posted(j.get("postedOn")),
                        employees=10000,       # only big groups are listed here
                        size_label="Grand groupe",
                    )
                    offers[uid]._wd = (host, tenant, site, path)
                    found += 1
                offset += PAGE
                if offset >= total or not jobs:
                    break
                time.sleep(0.3)
        if not found:
            print(f"[Workday {name}: 0 results — check the URL]", end=" ")
    _details(session, list(offers.values()), config)
    return list(offers.values())
