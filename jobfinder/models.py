"""Shared data model for a job offer, whatever the source."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Offer:
    uid: str            # stable unique id, e.g. "vie:12345"
    source: str         # "VIE", "Greenhouse", "WTTJ", ...
    company: str
    title: str
    location: str
    url: str
    description: str = ""   # plain-text snippet used for scoring
    contract: str = ""      # "VIE", "Internship", "Full-time", ...
    date: str = ""          # publication date if known (ISO string)
    start_date: str = ""    # mission/job start "YYYY-MM" if known
    employees: int | None = None  # company headcount if the source gives it
    size_label: str = ""          # e.g. "250-499", "2000+" (display only)
    score: int = 0
    is_new: bool = False
    region: str = ""        # "west", "south", "east", "visa" or "unknown"
    visa_ok: bool = False   # outside the EU and the offer says it sponsors
    salary_month: int | None = None  # monthly gross pay if stated (EUR)
    salary_label: str = ""  # e.g. "1 200 €/mois", "38 k€/an"
    lang: str = ""          # posting language if the source says it ("fr", "en"...)
    reasons: list = field(default_factory=list)  # why it scored
