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
    reasons: list = field(default_factory=list)  # why it scored
