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


def _parse(url: str):
    """https://sanofi.wd3.myworkdayjobs.com/en-US/SanofiCareers -> (host, tenant, site)."""
    u = urlparse(url.strip())
    parts = [p for p in u.path.split("/") if p]
    parts = [p for p in parts if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]  # drop locale
    if not parts:
        raise ValueError(f"no site name in {url}")
    return u.netloc, u.netloc.split(".")[0], parts[0]


def _posted(text: str) -> str:
    return (text or "").replace("Posted ", "").strip()


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
                        size_label="Large group",
                    )
                    found += 1
                offset += PAGE
                if offset >= total or not jobs:
                    break
                time.sleep(0.3)
        if not found:
            print(f"[Workday {name}: 0 results — check the URL]", end=" ")
    return list(offers.values())
