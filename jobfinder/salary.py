"""Find the pay stated in an offer and turn it into a monthly gross amount.

Sources give pay in very different ways:
- structured fields (Welcome to the Jungle, France Travail)
- free text: "Gratification : 1 200 € / mois", "€35,000 - €40,000 per year",
  "Salaire : 38k€ brut annuel", "RAL 30.000 EUR"
We only trust an amount if it sits next to a pay word (salaire, salary,
gratification, rémunération, compensation...) or a period word
(par mois, per year, annuel...), so revenue figures like "€2bn" are ignored.
The lower end of a range is used (conservative).
"""
from __future__ import annotations

import re

_NUM = r"(\d{1,3}(?:[ .,  ']\d{3})+|\d+(?:[.,]\d{1,2})?)"
_AMOUNT = re.compile(
    r"(?:(?:€|eur|euros?)\s*" + _NUM + r"\s*(k)?(?![\w.,]*\s*(?:m\b|mn|million|bn|billion|milliard)))"
    r"|(?:" + _NUM + r"\s*(k)?\s*(?:€|eur\b|euros?\b)(?!\s*(?:m\b|million|bn|billion|milliard)))"
)
_PAY_CUE = re.compile(
    r"salaire|salary|salario|remuner|gratification|compensation|indemnite|"
    r"\bpay\b|package|brut|gross|retribucion|sueldo|stipend|\bral\b|retribuzione")
_MONTH = re.compile(r"mois|month|mensuel|monthly|/\s*m\b|mensual|al mes|mese|mensile")
_YEAR = re.compile(r"\ban\b|annuel|annual|year|yearly|\bp\.?a\.?\b|/\s*an\b|anual|anno|annuo|\bk\b")


def _to_float(raw: str) -> float | None:
    s = raw.replace(" ", " ").replace(" ", " ").replace("'", " ")
    # "1 200" / "1.200" / "1,200" = thousands ; "12,5" / "12.5" = decimals
    if re.fullmatch(r"\d{1,3}(?:[ .,]\d{3})+", s):
        return float(re.sub(r"[ .,]", "", s))
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def monthly_from_text(text_folded: str) -> int | None:
    """Return the lowest monthly gross pay stated in the text, or None."""
    text = text_folded or ""
    best = None
    for m in _AMOUNT.finditer(text):
        raw = m.group(1) or m.group(3)
        kilo = m.group(2) or m.group(4)
        value = _to_float(raw)
        if value is None:
            continue
        if kilo:
            value *= 1000
        before = text[max(0, m.start() - 70):m.start()]
        after = text[m.end():m.end() + 40]
        around = before + " " + after
        if not (_PAY_CUE.search(around) or _MONTH.search(after) or _YEAR.search(after)):
            continue
        if _MONTH.search(after) or (_MONTH.search(before[-25:]) and not _YEAR.search(after)):
            monthly = value
        elif _YEAR.search(after) or _YEAR.search(before[-25:]) or kilo:
            monthly = value / 12
        else:
            monthly = value if value < 6000 else value / 12
        if 300 <= monthly <= 20000:
            best = monthly if best is None else min(best, monthly)
    return int(best) if best else None


def monthly_from_fields(minimum, maximum=None, period: str = "") -> int | None:
    """Structured salary fields -> monthly gross."""
    value = minimum if isinstance(minimum, (int, float)) and minimum > 0 else maximum
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    p = (period or "").lower()
    if "month" in p or "mens" in p:
        monthly = value
    elif "year" in p or "annu" in p:
        monthly = value / 12
    elif "day" in p or "jour" in p:
        monthly = value * 21
    elif "hour" in p or "heure" in p:
        monthly = value * 151
    else:
        monthly = value if value < 6000 else value / 12
    return int(monthly) if 300 <= monthly <= 20000 else None


def label(monthly: int | None) -> str:
    if not monthly:
        return ""
    if monthly >= 2500:
        return f"{round(monthly * 12 / 1000)} k€/an"
    return f"{monthly:,} €/mois".replace(",", " ")
