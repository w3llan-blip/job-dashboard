"""Fetch offers from Welcome to the Jungle (welcometothejungle.com).

The website's job search runs on Algolia with a public, search-only key
that every visitor's browser receives. We read that key from the site at
each run (falling back to the last known one), then run the searches
listed in config.yaml -> welcome_to_the_jungle.queries. Read-only, no
login, no account involved.

Company size: WTTJ is full of early-stage startups. Each company's
headcount is looked up once (then cached in org_sizes.json) and offers
from companies smaller than `min_employees` are dropped.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from ..models import Offer
from ..salary import monthly_from_fields, label as salary_label

SITE = "https://www.welcometothejungle.com"
ALGOLIA_APP = "CSEKHVMS53"
FALLBACK_KEY = "4bd8f6215d0cc52b26430765769e65a0"   # public search-only key
JOBS_INDEX = "wk_cms_jobs_production"
ORGS_INDEX = "wk_cms_organizations_production"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HITS_PER_PAGE = 100
CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "org_sizes.json"

# WTTJ contract codes -> what we show
CONTRACTS = {
    "internship": "Internship", "vie": "VIE", "graduate_program": "Graduate program",
    "full_time": "Full-time", "apprenticeship": "Apprenticeship",
    "temporary": "Fixed-term", "part_time": "Part-time", "freelance": "Freelance",
}


def _strip_html(text: str) -> str:
    import html as htmllib
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def _api_key(session: requests.Session) -> str:
    """Read the current public search key from the site; fall back if the
    page layout changed."""
    try:
        page = session.get(SITE + "/fr/jobs", timeout=20).text
        m = re.search(r'ALGOLIA_API_KEY[A-Z_]*\\?["\']\s*:\s*\\?["\']([0-9a-f]{32})', page)
        if m:
            return m.group(1)
    except requests.RequestException:
        pass
    return FALLBACK_KEY


def _search(session, key, index, params: str) -> dict:
    resp = session.post(
        f"https://{ALGOLIA_APP.lower()}-dsn.algolia.net/1/indexes/{index}/query",
        data=json.dumps({"params": params}),
        headers={
            "x-algolia-application-id": ALGOLIA_APP,
            "x-algolia-api-key": key,
            "content-type": "application/x-www-form-urlencoded",
            "origin": SITE, "referer": SITE + "/",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _find_employees(obj):
    """Look for a headcount anywhere in a record (field names vary)."""
    if isinstance(obj, dict):
        for k in ("nb_employees", "employees_count", "size"):
            v = obj.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return int(v)
            if isinstance(v, str) and v.isdigit():
                return int(v)
        for v in obj.values():
            found = _find_employees(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_employees(v)
            if found:
                return found
    return None


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _org_size(session, key, slug, name, cache) -> int | None:
    if slug in cache:
        return cache[slug]
    size = None
    try:
        data = _search(session, key, ORGS_INDEX,
                       f"query={requests.utils.quote(name)}&hitsPerPage=5")
        for hit in data.get("hits") or []:
            if hit.get("slug") == slug:
                size = _find_employees(hit)
                break
    except (requests.RequestException, ValueError):
        return None  # don't cache failures, retry next run
    cache[slug] = size
    time.sleep(0.2)
    return size


def _salary(hit) -> int | None:
    """WTTJ salary fields: names vary (salary_minimum, salary_yearly_minimum,
    salary_period...), so look for them by name."""
    mins, maxs, period = None, None, ""
    for k, v in hit.items():
        lk = k.lower()
        if "salary" not in lk:
            continue
        if isinstance(v, (int, float)) and v > 0:
            if "min" in lk and mins is None:
                mins = v
            elif "max" in lk and maxs is None:
                maxs = v
            if "year" in lk:
                period = period or "yearly"
            elif "month" in lk:
                period = period or "monthly"
        elif isinstance(v, str) and "period" in lk:
            period = v
    return monthly_from_fields(mins, maxs, period)


def _text(hit, *keys) -> str:
    parts = []
    for k in keys:
        v = hit.get(k)
        if isinstance(v, str):
            parts.append(_strip_html(v))
    return " ".join(parts)


def fetch(config: dict) -> list[Offer]:
    cfg = config.get("welcome_to_the_jungle") or {}
    queries = cfg.get("queries") or []
    max_pages = int(cfg.get("pages_per_query") or 2)
    size_cfg = config.get("company_size") or {}
    min_emp = int(size_cfg.get("min_employees") or 0)
    keep_unknown = bool(size_cfg.get("keep_unknown", True))

    session = requests.Session()
    session.headers["User-Agent"] = UA
    key = _api_key(session)
    cache = _load_cache()

    hits = {}
    for q in queries:
        for page in range(max_pages):
            params = (f"query={requests.utils.quote(q)}"
                      f"&hitsPerPage={HITS_PER_PAGE}&page={page}")
            data = _search(session, key, JOBS_INDEX, params)
            batch = data.get("hits") or []
            for h in batch:
                hits.setdefault(h.get("objectID") or h.get("slug"), h)
            if page + 1 >= (data.get("nbPages") or 0):
                break
            time.sleep(0.3)

    offers: list[Offer] = []
    small = 0
    for h in hits.values():
        org = h.get("organization") or {}
        org_slug = org.get("slug") or ""
        org_name = (org.get("name") or "").strip()
        employees = _find_employees(org) or _org_size(session, key, org_slug, org_name, cache)
        if employees is not None and employees < min_emp:
            small += 1
            continue
        if employees is None and not keep_unknown:
            continue

        office = h.get("office") or {}
        if not office and isinstance(h.get("offices"), list) and h["offices"]:
            office = h["offices"][0]
        location = ", ".join(x for x in ((office.get("city") or "").strip(),
                                          (office.get("country") or "").strip()) if x)
        contract_code = h.get("contract_type") or ""
        offers.append(Offer(
            uid=f"wttj:{h.get('reference') or h.get('slug')}",
            source="WTTJ",
            company=org_name,
            title=(h.get("name") or "").strip(),
            location=location,
            url=f"{SITE}/fr/companies/{org_slug}/jobs/{h.get('slug')}",
            description=_text(h, "summary", "description", "profile",
                              "key_missions", "recruitment_process")[:4000],
            contract=CONTRACTS.get(contract_code, contract_code.replace("_", " ").title()),
            date=(h.get("published_at") or "")[:10],
            start_date=(h.get("start_date") or "")[:7] if isinstance(h.get("start_date"), str) else "",
            employees=employees,
            size_label=f"{employees}" if employees else "",
            salary_month=(sal := _salary(h)),
            salary_label=salary_label(sal),
            lang=(h.get("language") or "")[:2].lower() if isinstance(h.get("language"), str) else "",
        ))

    try:
        CACHE_PATH.write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    if small:
        print(f"[WTTJ: {small} offers dropped, company < {min_emp} people]", end=" ")
    return offers
