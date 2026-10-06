"""Score offers against the preferences in config.yaml.

Rules:
- an "exclude" word in the title  -> offer dropped
- an "include" word in the title  -> +10 each (at least one required)
- a "boost" word in title/descr.  -> +2 each
- location matches a preferred place -> +5
- start date stated and inside the window -> +3
- company smaller than company_size.min_employees -> dropped
- outside EU/EEA/Switzerland -> kept only if VIE or visa sponsorship is
  stated (+4, "VISA" badge)
- internship/VIE detected -> tagged (no penalty, they're wanted too)
"""
import re
import unicodedata

from .models import Offer
from .regions import region, sponsors_visa

INTERNSHIP_WORDS = ("intern", "internship", "stage", "stagiaire", "alternance", "apprenticeship")


def _norm(text: str) -> str:
    return " " + (text or "").lower() + " "


def _fold(text: str) -> str:
    """Lowercase, remove accents, French gender markers and extra spaces so
    'Chargé(e) de projet (H/F)' matches 'charge de projet'."""
    text = (text or "").lower().replace("\u2019", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # remove gender markers: (e), (h/f), (f/h), (m/f), (f/m), (m/w), (w/m), ·e, .e
    text = re.sub(r"\((?:e|es|h/f|f/h|m/f|f/m|m/w|w/m|h/f/x|m/f/d)\)", "", text)
    text = re.sub(r"[·.]e\b", "", text)
    return re.sub(r"\s+", " ", text)


def _has_word(word: str, text: str) -> bool:
    """True if `word` appears as a whole word/phrase in `text`
    (so 'vp' matches 'VP, Sales' but not 'MVP')."""
    return re.search(r"\b" + re.escape(word.strip()) + r"\b", text) is not None


# --- start-date detection in free text (English + French) ---------------

_MONTHS = {
    "january": 1, "jan": 1, "janvier": 1,
    "february": 2, "feb": 2, "fevrier": 2,
    "march": 3, "mar": 3, "mars": 3,
    "april": 4, "apr": 4, "avril": 4,
    "may": 5, "mai": 5,
    "june": 6, "jun": 6, "juin": 6,
    "july": 7, "jul": 7, "juillet": 7,
    "august": 8, "aug": 8, "aout": 8,
    "september": 9, "sep": 9, "sept": 9, "septembre": 9,
    "october": 10, "oct": 10, "octobre": 10,
    "november": 11, "nov": 11, "novembre": 11,
    "december": 12, "dec": 12, "decembre": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_CUES = (r"(?:start(?:ing|s)?(?:\s+date)?|begin(?:ning)?|commence|as of|from|"
         r"debut|demarrage|a partir de|des|prise de poste|disponible|available)")

_PATTERNS = [
    # "starting April 2027" / "début : avril 2027"
    re.compile(_CUES + r"\W{0,15}(?:\w+\W{1,3}){0,3}?(" + _MONTH_RE + r")\w*\W{1,3}(20\d{2})"),
    # "start: 04/2027"
    re.compile(_CUES + r"\W{0,15}(0?[1-9]|1[0-2])\s*/\s*(20\d{2})"),
]


def extract_start_date(text: str) -> str:
    """Return 'YYYY-MM' if the text states a job start date, else ''."""
    t = _fold(text)
    for pat in _PATTERNS:
        m = pat.search(t)
        if m:
            month_raw, year = m.group(1), m.group(2)
            month = _MONTHS.get(month_raw, None) if not month_raw.isdigit() else int(month_raw)
            if month:
                return f"{year}-{month:02d}"
    return ""


def score_offers(offers: list[Offer], config: dict) -> list[Offer]:
    kw = config.get("keywords") or {}
    include = [w.lower() for w in kw.get("include") or []]
    boost = [w.lower() for w in kw.get("boost") or []]
    exclude = [w.lower() for w in kw.get("exclude") or []]
    bad_companies = [c.lower() for c in config.get("exclude_companies") or []]
    # disqualifiers: plain phrases, or regex patterns prefixed with "re:"
    dq_plain, dq_regex = [], []
    for d in config.get("disqualifiers") or []:
        if d.startswith("re:"):
            dq_regex.append(re.compile(_fold(d[3:])))
        else:
            dq_plain.append(_fold(d))
    window = config.get("start_window") or {}
    win_from = str(window.get("from") or "")
    win_to = str(window.get("to") or "")
    keep_undated = bool(window.get("keep_undated"))
    preferred = [p.lower() for p in (config.get("locations") or {}).get("preferred") or []]
    size_cfg = config.get("company_size") or {}
    min_emp = int(size_cfg.get("min_employees") or 0)
    visa_rule = bool((config.get("visa") or {}).get("non_eu_requires_sponsorship", True))

    # fold accents everywhere so "chargé" matches "charge", etc.
    include = [_fold(w) for w in include]
    boost = [_fold(w) for w in boost]
    exclude = [_fold(w) for w in exclude]
    bad_companies = [_fold(c) for c in bad_companies]
    preferred = [_fold(p) for p in preferred]

    kept: list[Offer] = []
    for o in offers:
        title = _fold(o.title)
        desc = _fold(o.description)
        loc = _fold(o.location)
        company = _fold(o.company)

        if any(_has_word(x, title) for x in exclude):
            continue
        if any(_has_word(c, company) for c in bad_companies):
            continue
        if o.employees is not None and o.employees < min_emp:
            continue  # too small (startup)
        folded_desc = _fold(o.description)
        if any(d in folded_desc for d in dq_plain):
            continue
        if any(p.search(folded_desc) for p in dq_regex):
            continue

        # visa: free to work in the EU/EEA/CH; elsewhere only VIEs or
        # offers that say they sponsor the visa
        # "VIE" must be written in capitals: "Assurance Vie" is not a VIE
        vie_in_title = re.search(r"\bV\.?I\.?E\b", o.title) is not None
        is_vie = o.source == "VIE" or o.contract == "VIE" or vie_in_title
        o.region = region(loc)
        o.visa_ok = o.region == "visa" and not is_vie and sponsors_visa(folded_desc)
        if visa_rule and o.region == "visa" and not is_vie and not o.visa_ok:
            continue

        # start-date window filter
        date_fits = False
        if win_from and win_to:
            if not o.start_date:
                o.start_date = extract_start_date(o.description)
            if o.start_date:
                if not (win_from <= o.start_date <= win_to):
                    continue
                date_fits = True
            elif not keep_undated:
                continue

        is_vie_title = vie_in_title
        matched = [w for w in include if _has_word(w, title)]
        if is_vie_title:
            matched.append("vie")
        if not matched:
            continue
        o.score = 10 * len(matched)
        o.reasons = [f"title: {w}" for w in matched]
        if date_fits:
            o.score += 3
            o.reasons.append("start date fits")
        if o.visa_ok:
            o.score += 4
            o.reasons.append("visa sponsorship mentioned")

        boosted = [w for w in boost if _has_word(w, title) or _has_word(w, desc)]
        o.score += 2 * len(boosted)
        o.reasons += [f"boost: {w}" for w in boosted]

        if any(p in loc for p in preferred) or o.source == "VIE":
            o.score += 5
            o.reasons.append("location match")

        # companies sometimes advertise VIE roles on their own boards
        if o.source != "VIE" and is_vie_title:
            o.contract = "VIE"
        if not o.contract:
            o.contract = "Internship" if any(w in title for w in INTERNSHIP_WORDS) else "Full-time"

        kept.append(o)

    kept.sort(key=lambda o: (o.is_new, o.score), reverse=True)
    return kept
