"""Fetch VIE/VIA offers from the official Business France site
(mon-vie-via.businessfrance.fr).

The site's own public access key is read from the page at each run,
exactly like a normal browser visit, then the same search endpoint the
website uses is queried. Read-only, no login, no account involved.
"""
import re
import html as htmllib

import requests

from ..models import Offer

SITE = "https://mon-vie-via.businessfrance.fr"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAGE_SIZE = 100
MAX_OFFERS = 4000  # safety cap


def _get_api_config(session: requests.Session):
    """Read the API endpoint + public key from the site's page config."""
    page = session.get(SITE + "/offres/recherche", timeout=30).text
    key_m = re.search(r"API_KEY[\"']?\s*[:=]\s*[\"']([^\"']+)[\"']", page)
    ep_m = re.search(r"OFFRE_API_ENDPOINT[\"']?\s*[:=]\s*[\"']([^\"']+)[\"']", page)
    if not key_m or not ep_m:
        raise RuntimeError("Could not read VIE site configuration (site layout may have changed).")
    key = key_m.group(1).encode().decode("unicode_escape")
    endpoint = ep_m.group(1).encode().decode("unicode_escape").rstrip("/")
    return endpoint, key


def _strip_html(text: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def fetch(config: dict) -> list[Offer]:
    session = requests.Session()
    session.headers["User-Agent"] = UA
    endpoint, key = _get_api_config(session)

    offers: list[Offer] = []
    skip = 0
    total = None
    while skip < MAX_OFFERS:
        body = {
            "limit": PAGE_SIZE, "skip": skip, "query": "",
            "activitySectorId": [], "missionsTypesIds": [],
            "missionsDurations": [], "gerographicZones": [],
            "countriesIds": [], "studiesLevelId": [],
            "companiesSizes": [], "specializationsIds": [],
            "entreprisesIds": [0], "missionStartDate": None,
        }
        resp = session.post(endpoint + "/search", json=body,
                            headers={"X-API-KEY": key}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if total is None:
            total = data.get("count") or 0
        batch = data.get("result") or []
        if not batch:
            break
        for o in batch:
            oid = o.get("id")
            city = (o.get("cityName") or "").strip().title()
            country = (o.get("countryName") or "").strip().title()
            location = ", ".join(x for x in (city, country) if x)
            offers.append(Offer(
                uid=f"vie:{oid}",
                source="VIE",
                company=(o.get("organizationName") or "").strip(),
                title=(o.get("missionTitle") or "").strip(),
                location=location,
                url=f"{SITE}/offres/{oid}",
                description=_strip_html(
                    (o.get("missionDescription") or "") + " " + (o.get("missionProfile") or "")
                )[:4000],
                contract=f"VIE ({o.get('missionDuration')} months)" if o.get("missionDuration") else "VIE",
                date=(o.get("creationDate") or "")[:10],
                start_date=(o.get("missionStartDate") or "")[:7],
            ))
        skip += PAGE_SIZE
        if skip >= total:
            break
    return offers
