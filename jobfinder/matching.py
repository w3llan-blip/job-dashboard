"""Filter offers against config.yaml, then rank them (score out of 100).

Filters (offer dropped):
- an "exclude" word in the title (tech, senior, marketing roles...)
- no "include" word in the title (and not a VIE)
- excluded company, company smaller than company_size.min_employees
- a disqualifier in the description (degree you don't have, no visa...)
- Eastern Europe; Southern Europe without a decent stated salary
  (VIEs pass: the allowance is set by Business France); outside Europe
  unless VIE or visa sponsorship stated
- another language required / Spanish only / offer written in another
  language (see languages.py)
- start date outside the window; 5+ years of experience asked
- not a VIE, an internship or a graduate program (the only contracts
  your school accepts to validate the master's) — apprenticeships too

Ranking (see _rank): role 35, level/contract 20, start date 10,
company 10, location 10, salary 8, freshness 7, bonus words up to 5.
Each point is explained in offer.reasons (shown under "Détails").
"""
import re
import unicodedata

from .models import Offer
from .regions import region, sponsors_visa
from .languages import language_problem
from .salary import monthly_from_text, label as salary_label

# why offers were dropped in the last run (shown in the "Sources" tab)
LAST_DROPS: dict = {}
# the "ideal:" section of config.yaml, folded (set by score_offers)
IDEAL: dict = {}
AI_CASE_RE = re.compile(r"\b(?:AI|IA|GenAI|GenIA|LLMs?)\b")

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


_EXP = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|a|to|à)?\s*(?:\d{1,2}\s*)?"
    r"(?:years?|yrs?|ans|anos|annees)\s*(?:minimum\s*)?(?:of\s*|d\s*'?\s*|de\s*)?"
    r"(?:relevant\s*|professional\s*|work\s*)?(?:experience|exp)")
INTERN_RE = re.compile(r"intern\b|internship|\bstage\b|stagiaire|praktik|practicas|tirocinio|"
                       r"becario|stagiair")
# internship stated only in the description ("stage de fin d'études"...)
INTERN_DESC_RE = re.compile(r"stage de fin d.?etudes|end.of.studies internship|"
                            r"\b[4-6].?(?:month|mois) internship|stage de [4-6] mois|"
                            r"internship of [4-6] months|convention de stage")
GRAD_RE = re.compile(r"graduate|trainee|rotational|leadership (?:development )?program|"
                     r"programme? jeunes? diplomes?|young graduate|early careers? program")
# words that describe the contract format, not the job (no role points)
FORMAT_WORDS = {"graduate", "graduate program", "graduate programme", "management trainee",
                "rotational", "leadership program"}
# apprenticeships don't validate the master's degree
APPRENTICE_RE = re.compile(r"alternan|apprenti|work.study|contrat pro|werkstudent|"
                           r"working student|dual study|duales studium")


def _years_asked(desc: str) -> int:
    years = [int(m.group(1)) for m in _EXP.finditer(desc)]
    years = [y for y in years if 0 < y < 20]
    return min(years) if years else 0


def _days_old(date: str):
    from datetime import date as d
    try:
        return (d.today() - d.fromisoformat(date[:10])).days
    except (ValueError, TypeError):
        return None


def _drop(reason: str) -> None:
    LAST_DROPS[reason] = LAST_DROPS.get(reason, 0) + 1


def score_offers(offers: list[Offer], config: dict) -> list[Offer]:
    LAST_DROPS.clear()
    IDEAL.clear()
    for k, v in (config.get("ideal") or {}).items():
        IDEAL[k] = [_fold(x) for x in v or []]
    kw = config.get("keywords") or {}
    fold_all = lambda xs: [_fold(x) for x in xs or []]
    include = fold_all(kw.get("include"))
    priority = fold_all(kw.get("priority"))
    include = list(dict.fromkeys(include + priority))   # priority roles count as included
    boost = fold_all(kw.get("boost"))
    exclude = fold_all(kw.get("exclude"))
    bad_companies = fold_all(config.get("exclude_companies"))
    dq_plain, dq_regex = [], []
    for d in config.get("disqualifiers") or []:
        if d.startswith("re:"):
            dq_regex.append(re.compile(_fold(d[3:])))
        else:
            dq_plain.append(_fold(d))
    window = config.get("start_window") or {}
    win_from, win_to = str(window.get("from") or ""), str(window.get("to") or "")
    intern_from = str(window.get("internship_from") or win_from)
    keep_undated = bool(window.get("keep_undated"))
    preferred = fold_all((config.get("locations") or {}).get("preferred"))
    min_emp = int((config.get("company_size") or {}).get("min_employees") or 0)
    visa_cfg = config.get("visa") or {}
    visa_rule = bool(visa_cfg.get("non_eu_requires_sponsorship", True))
    intern_ok_places = fold_all(visa_cfg.get("internship_ok_without_sponsorship"))
    never_places = fold_all(visa_cfg.get("never_except_vie"))
    sal = config.get("salary") or {}
    south_min_intern = int(sal.get("south_europe_min_internship_month") or 1000)
    south_min = int(sal.get("south_europe_min_month") or 2500)
    lang_rule = bool((config.get("languages") or {}).get("enabled", True))
    only_school_ok = bool((config.get("contracts") or {}).get("only_vie_internship_graduate", True))

    kept: list[Offer] = []
    for o in offers:
        title = _fold(o.title)
        desc = _fold(o.description)
        loc = _fold(o.location)
        company = _fold(o.company)

        if any(_has_word(x, title) for x in exclude):
            _drop("mot exclu dans le titre (tech, senior, marketing…)")
            continue
        vie_in_title = re.search(r"\bV\.?I\.?E\b", o.title) is not None
        is_vie = o.source == "VIE" or o.contract == "VIE" or vie_in_title
        matched = [w for w in include if _has_word(w, title)]
        if not matched:   # a VIE must also be in one of your roles
            _drop("titre hors de tes métiers")
            continue
        if any(_has_word(c, company) for c in bad_companies):
            _drop("entreprise exclue (cabinets de conseil…)")
            continue
        if o.employees is not None and o.employees < min_emp:
            _drop(f"entreprise de moins de {min_emp} personnes")
            continue
        if any(d in desc for d in dq_plain) or any(p.search(desc) for p in dq_regex):
            _drop("exigence que tu n'as pas (diplôme, visa…)")
            continue
        years = _years_asked(desc)
        if years >= 5:
            _drop("5 ans d'expérience ou plus demandés")
            continue

        # pay
        if not o.salary_month:
            o.salary_month = monthly_from_text(desc)
            o.salary_label = salary_label(o.salary_month)
        kind = _fold(o.contract) + " " + title
        is_intern = bool(INTERN_RE.search(kind) or INTERN_DESC_RE.search(desc[:1500]))
        is_grad = bool(GRAD_RE.search(kind))
        if only_school_ok:
            if APPRENTICE_RE.search(kind) and not is_vie:
                _drop("alternance (non acceptée par l'école)")
                continue
            if not (is_vie or is_intern or is_grad):
                _drop("emploi (ni VIE, ni stage, ni graduate program)")
                continue

        # where
        o.region = region(loc)
        o.visa_ok = o.region == "visa" and not is_vie and sponsors_visa(desc)
        if o.region == "east":
            _drop("Europe de l'Est")
            continue
        if o.region == "south" and not is_vie:
            need = south_min_intern if is_intern else south_min
            if not o.salary_month:
                _drop("Europe du Sud sans salaire affiché")
                continue
            if o.salary_month < need:
                _drop("Europe du Sud avec salaire trop bas")
                continue
        o.permit_ok = False
        if o.region == "visa" and not is_vie and any(_has_word(w, loc) for w in never_places):
            _drop("États-Unis hors VIE")
            continue
        if (o.region == "visa" and is_intern and not is_vie and not is_grad
                and any(_has_word(w, loc) for w in intern_ok_places)):
            o.permit_ok = True   # e.g. Canada co-op internship permit
        if visa_rule and o.region == "visa" and not is_vie and not o.visa_ok and not o.permit_ok:
            _drop("hors Europe sans VIE ni sponsoring de visa")
            continue

        # language
        if lang_rule:
            problem = language_problem(desc, o.lang)
            if problem:
                _drop("langue : " + problem)
                continue

        # start date
        date_fits = False
        if win_from and win_to:
            if not o.start_date:
                o.start_date = extract_start_date(o.description)
            # internships start later (end of the master's); VIE / grad keep win_from
            start_min = intern_from if (is_intern and not is_vie and not is_grad) else win_from
            if o.start_date:
                if not (start_min <= o.start_date <= win_to):
                    _drop("date de début hors de ta fenêtre")
                    continue
                date_fits = True
            elif not keep_undated:
                _drop("pas de date de début")
                continue

        if o.source != "VIE" and vie_in_title:
            o.contract = "VIE"
        if is_intern and not is_vie and not is_grad:
            o.contract = "Stage"
        elif is_grad and not is_vie:
            o.contract = "Graduate program"
        elif not o.contract:
            o.contract = "Full-time"

        _rank(o, title, desc, loc, matched, priority, boost, preferred,
              is_vie, is_intern, date_fits, years, south_min_intern, south_min)
        kept.append(o)

    kept.sort(key=lambda o: o.score, reverse=True)
    if LAST_DROPS:
        print("Dropped: " + ", ".join(f"{k} ({v})" for k, v in
                                      sorted(LAST_DROPS.items(), key=lambda kv: -kv[1])))
    return kept


def _rank(o, title, desc, loc, matched, priority, boost, preferred,
          is_vie, is_intern, date_fits, years, south_min_intern, south_min):
    """Score out of 100 with a reason for every point."""
    pts, why = 0, []

    def add(n, text):
        nonlocal pts
        pts += n
        why.append(f"{text} (+{n})" if n >= 0 else f"{text} ({n})")

    # 1. role (35) — format words ("graduate program"...) say nothing
    # about the job itself: they are scored in part 2, not here
    roles = [w for w in matched if w not in FORMAT_WORDS]
    top = [w for w in roles if w in priority]
    if top:
        add(35 if len(set(roles)) > 1 else 32, "métier cœur de cible : " + ", ".join(dict.fromkeys(top)))
    elif roles:
        add(22 if len(set(roles)) > 1 else 20, "métier compatible : " + ", ".join(dict.fromkeys(roles)))
    else:
        add(12, "métier non précisé dans le titre (seulement le format)")

    # 2. level / contract (20)
    kind = (o.contract + " " + title).lower()
    if is_vie:
        add(20, "VIE")
    elif GRAD_RE.search(_fold(kind)):
        add(20, "graduate program")
    elif is_intern:
        add(18, "stage")
    else:
        add(8, "contrat non précisé")
    if years >= 3:
        add(-18, f"{years} ans d'expérience demandés")
    elif years == 2:
        add(-4, "2 ans d'expérience demandés")

    # 3. start date (10)
    add(10, "date de début dans ta fenêtre") if date_fits else add(4, "date de début non indiquée")

    # 4. company (10)
    e = o.employees
    if e and e >= 5000:
        add(10, "grand groupe")
    elif e and e >= 1000:
        add(8, "grande entreprise")
    elif e:
        add(6, "scale-up / ETI")
    else:
        add(5 if is_vie else 4, "taille inconnue")

    # 5. location (10)
    if o.region == "west":
        add(10 if any(p in loc for p in preferred) else 8, "Europe de l'Ouest / du Nord")
    elif o.region == "south":
        add(7, "Europe du Sud (salaire correct)")
    elif o.region == "visa":
        if is_vie:
            add(6, "hors Europe (VIE)")
        elif getattr(o, "permit_ok", False):
            add(6, "Canada : permis stage coop (EIC) à demander toi-même")
        else:
            add(6, "hors Europe, visa sponsorisé")
    else:
        add(5, "lieu non reconnu")

    # 6. salary (8)
    need = south_min_intern if is_intern else south_min
    if o.salary_month and o.salary_month >= need:
        add(8, f"salaire affiché : {o.salary_label}")
    elif o.salary_month:
        add(3, f"salaire affiché mais bas : {o.salary_label}")
    elif is_vie:
        add(6, "indemnité VIE")

    # 7. freshness (7)
    age = _days_old(o.date)
    if age is None:
        add(3, "date de publication inconnue")
    elif age <= 7:
        add(7, "publiée cette semaine")
    elif age <= 21:
        add(4, "publiée il y a moins de 3 semaines")
    elif age <= 45:
        add(2, "publiée il y a plus de 3 semaines")
    else:
        add(0, "publiée il y a plus de 6 semaines")

    # 8. bonus words (5)
    boosted = [w for w in boost if _has_word(w, title) or _has_word(w, desc)]
    if boosted:
        add(min(5, len(boosted)), "mots bonus : " + ", ".join(boosted[:5]))
    if o.visa_ok:
        why.append("visa sponsorisé mentionné")

    # 9. your ideal internship (bonus up to +15, penalty -12)
    bonus, hits = _ideal(o, title, desc, loc)
    o.ideal = False
    if bonus < 0:
        add(bonus, "pas ton style : " + ", ".join(hits))
    elif bonus > 0:
        add(bonus, "proche de ton stage idéal : " + ", ".join(hits))
        o.ideal = bonus >= 10

    o.score = max(0, min(100, pts))
    o.reasons = why


def _ideal(o, title, desc, loc):
    """Bonus for your ideal internship (strategy, change management around
    AI/tech, international), penalty for Excel-heavy or local roles."""
    if not IDEAL:
        return 0, []
    off = [w for w in IDEAL.get("turnoffs", []) if _has_word(w, title)]
    if off:
        return -12, off
    pts, hits = 0, []

    def theme(name, label, in_title, in_desc):
        nonlocal pts
        words = IDEAL.get(name, [])
        if any(_has_word(w, title) for w in words):
            pts += in_title
            hits.append(label + " (titre)")
        elif any(_has_word(w, desc) for w in words):
            pts += in_desc
            hits.append(label)

    theme("strategy", "stratégie", 6, 2)
    theme("change", "transformation / changement", 6, 3)
    # AI: config words + the short acronyms, matched case-sensitive
    ai_title = AI_CASE_RE.search(o.title or "") or any(_has_word(w, title) for w in IDEAL.get("ai", []))
    ai_desc = AI_CASE_RE.search(o.description or "") or any(_has_word(w, desc) for w in IDEAL.get("ai", []))
    if ai_title:
        pts += 6
        hits.append("IA (titre)")
    elif ai_desc:
        pts += 4
        hits.append("IA")
    theme("international", "international", 3, 2)
    if any(_has_word(c, loc) for c in IDEAL.get("cities", [])):
        pts += 3
        hits.append("ville cible")
    return min(15, pts), hits
