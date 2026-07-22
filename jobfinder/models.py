"""Shared data model for a job offer, whatever the source."""
from dataclasses import dataclass, field


@dataclass
class Offer:
    uid: str            # stable unique id, e.g. "vie:12345"
    source: str         # "VIE", "Greenhouse", "Lever"
    company: str
    title: str
    location: str
    url: str
    description: str = ""   # plain-text snippet used for scoring
    contract: str = ""      # "VIE", "Internship", "Full-time", ...
    date: str = ""          # publication date if known (ISO string)
    score: int = 0
    is_new: bool = False
    reasons: list = field(default_factory=list)  # why it scored
