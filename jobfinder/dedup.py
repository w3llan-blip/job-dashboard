"""Remove the same offer seen on several sites (e.g. a company's own
Workday page and its Welcome to the Jungle copy).

Two offers are the same when, once cleaned, they have the same title and
the same company (the rule used before, now tolerant to spelling noise),
or exactly the same link. Cleaning removes accents, punctuation, gender
markers ("H/F", "F/H", "m/f/d", "all genders"...) and legal or country
suffixes of company names ("Accenture France" = "Accenture"). Contract
words ("stage", "CDI"...) are kept, so an internship is never merged with
a permanent job of the same title.

Sources are fetched in the order of main.SOURCES (direct company sources
first), so the first copy wins; empty fields of the kept copy (start date,
description, salary...) are filled from the duplicates.
"""
from __future__ import annotations

import re
import unicodedata

_GENDER = re.compile(
    r"\(\s*[hfmwxd]\s*/\s*[hfmwxd](?:\s*/\s*[hfmwxd])?\s*\)"   # (H/F), (m/f/d)
    r"|\b[hfmw]\s*/\s*[hfmw](?:\s*/\s*[xd])?\b"                # H/F, m/w/d
    r"|\ball[\s-]*genders?\b|\bshe\s*/\s*he\s*/\s*they\b|\(\s*e\s*\)"
)
_COMPANY_NOISE = re.compile(
    r"\b(group|groupe|sa|sas|se|ag|nv|bv|inc|ltd|llc|gmbh|plc|france|the)\b")
_FILLABLE = ("description", "start_date", "salary_month", "salary_label",
             "employees", "size_label", "date", "lang")


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def norm_title(s: str) -> str:
    s = _GENDER.sub(" ", _ascii(s))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def norm_company(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", _ascii(s))
    return re.sub(r"\s+", " ", _COMPANY_NOISE.sub(" ", s)).strip()


def offer_key(o) -> tuple:
    company = norm_company(o.company) or (o.company or "").strip().lower()
    return (norm_title(o.title) or o.title.strip().lower(), company)


def dedupe(offers):
    """Return (unique offers, number of duplicates removed)."""
    kept, by_key, by_url = [], {}, {}
    removed = 0
    for o in offers:
        url = (o.url or "").split("#")[0].rstrip("/")
        first = by_key.get(offer_key(o)) or (by_url.get(url) if url else None)
        if first is not None:
            removed += 1
            for f in _FILLABLE:
                if not getattr(first, f, None) and getattr(o, f, None):
                    setattr(first, f, getattr(o, f))
            continue
        by_key[offer_key(o)] = o
        if url:
            by_url[url] = o
        kept.append(o)
    return kept, removed
