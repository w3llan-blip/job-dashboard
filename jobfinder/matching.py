"""Score offers against the preferences in config.yaml.

Rules:
- an "exclude" word in the title  -> offer dropped
- an "include" word in the title  -> +10 each (at least one required)
- a "boost" word in title/descr.  -> +2 each
- location matches a preferred place -> +5
- internship/VIE detected -> tagged (no penalty, they're wanted too)
"""
import re

from .models import Offer

INTERNSHIP_WORDS = ("intern", "internship", "stage", "stagiaire", "alternance", "apprenticeship")


def _norm(text: str) -> str:
    return " " + (text or "").lower() + " "


def _has_word(word: str, text: str) -> bool:
    """True if `word` appears as a whole word/phrase in `text`
    (so 'vp' matches 'VP, Sales' but not 'MVP')."""
    return re.search(r"\b" + re.escape(word.strip()) + r"\b", text) is not None


def score_offers(offers: list[Offer], config: dict) -> list[Offer]:
    kw = config.get("keywords") or {}
    include = [w.lower() for w in kw.get("include") or []]
    boost = [w.lower() for w in kw.get("boost") or []]
    exclude = [w.lower() for w in kw.get("exclude") or []]
    preferred = [p.lower() for p in (config.get("locations") or {}).get("preferred") or []]

    kept: list[Offer] = []
    for o in offers:
        title = _norm(o.title)
        desc = _norm(o.description)
        loc = _norm(o.location)

        if any(_has_word(x, title) for x in exclude):
            continue

        matched = [w for w in include if _has_word(w, title)]
        if not matched:
            continue
        o.score = 10 * len(matched)
        o.reasons = [f"title: {w}" for w in matched]

        boosted = [w for w in boost if _has_word(w, title) or _has_word(w, desc)]
        o.score += 2 * len(boosted)
        o.reasons += [f"boost: {w}" for w in boosted]

        if any(p in loc for p in preferred) or o.source == "VIE":
            o.score += 5
            o.reasons.append("location match")

        if not o.contract:
            o.contract = "Internship" if any(w in title for w in INTERNSHIP_WORDS) else "Full-time"

        kept.append(o)

    kept.sort(key=lambda o: (o.is_new, o.score), reverse=True)
    return kept
