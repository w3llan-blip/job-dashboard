"""Language rule: the job must work in French and/or English (Spanish is
fine as an extra, but not as the only working language).

Two checks on the offer text (accent-folded, lowercased):
1. In which language is the offer written? An offer written in German,
   Dutch, Italian, Portuguese... means that language is needed. An offer
   written in Spanish is kept only if it also asks for English or French.
2. Does a sentence require another language ("fluent German", "allemand
   courant exigé", "Dutch is a must")? Sentences saying it's a plus
   ("a plus", "un atout", "nice to have") or offering a choice
   ("English or German") don't count.
Offers with little or no text (title only) are kept: nothing to check.
"""
from __future__ import annotations

import re

STOPWORDS = {
    "en": "the and of to in for with you we our will your are is on as be this have an or at".split(),
    "fr": "le la les de des et du un une pour vous nous dans avec sur est au aux en votre notre sont".split(),
    "es": "el la los las de del y en para con que por una un su sus es nuestro tu experiencia".split(),
    "de": "der die das und mit fur von ist wir sie ein eine zu im den dem auf bei unser ihre".split(),
    "nl": "de het een en van voor met je wij ons is op te bij jouw onze naar".split(),
    "it": "il la di e che per con un una del della sono nel nella le gli dei tua nostro".split(),
    "pt": "o a os as de do da e em para com um uma que no na sua nosso voce".split(),
    "sv": "och att det som en ett med for pa av till vi du har ar din vara".split(),
    "da": "og at det som en et med for pa af til vi du har er din vores".split(),
    "pl": "i w z na do sie jest dla oraz nie od jak przez naszym".split(),
}
OK_LANGS = {"en", "fr"}

# languages you don't speak (folded, EN + FR + native names)
OTHER = [
    "german", "allemand", "deutsch", "dutch", "neerlandais", "nederlands",
    "flemish", "flamand", "italian", "italien", "italiano", "portuguese",
    "portugais", "portugues", "polish", "polonais", "swedish", "suedois",
    "danish", "danois", "norwegian", "norvegien", "finnish", "finnois",
    "czech", "tcheque", "hungarian", "hongrois", "romanian", "roumain",
    "greek", "grec", "japanese", "japonais", "mandarin", "chinese", "chinois",
    "cantonese", "korean", "coreen", "arabic", "arabe", "russian", "russe",
    "turkish", "turc", "hebrew", "hebreu", "hindi", "thai", "vietnamese",
]
SPANISH = ["spanish", "espagnol", "espanol", "castellano"]
OK_WORDS = ["english", "anglais", "ingles", "inglese", "englisch", "engels",
            "french", "francais", "frances", "francese", "franzosisch", "frans"]

_REQUIRED = re.compile(
    r"fluen|native|mother tongue|required|require|must|mandatory|essential|"
    r"proficien|business level|professional level|working knowledge|"
    r"speak|courant|bilingue|maitrise|maitriser|imperati|exige|obligatoire|"
    r"indispensable|parlant|parle|niveau|\bc1\b|\bc2\b|\bb2\b|"
    r"imprescindible|nativo|dominio|requisito|fliessend|verhandlungssicher|vloeiend")
_PLUS = re.compile(
    r"a plus|is a plus|an asset|nice to have|advantage|bonus|preferred|"
    r"desirable|appreci|un plus|un atout|souhaite|idealement|serait un|"
    r"valorara|se valora|deseable|ventaja|would be")
# the sentence must really be about speaking a language ("Chinese market"
# alone is not a language requirement)
_LANG_CTX = re.compile(
    r"fluen|native|mother tongue|speak|spoken|language|langue|idioma|lingua|"
    r"parl|courant|bilingue|written|oral|ecrit|\bc1\b|\bc2\b|\bb2\b|proficien|"
    r"fliessend|sprach|vloeiend|nativo")
_CHOICE = re.compile(r"\bor\b|\bou\b|\bo\b|and/or|et/ou|y/o")


def _has(words, text):
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) for w in words)


def posting_language(text_folded: str) -> str:
    words = re.findall(r"[a-z]+", text_folded or "")
    if len(words) < 40:
        return ""
    counts = {lang: 0 for lang in STOPWORDS}
    sets = {lang: set(ws) for lang, ws in STOPWORDS.items()}
    for w in words:
        for lang, ws in sets.items():
            if w in ws:
                counts[lang] += 1
    lang, best = max(counts.items(), key=lambda kv: kv[1])
    return lang if best >= max(6, len(words) * 0.06) else ""


def language_problem(text_folded: str, hint: str = "") -> str:
    """'' if fine, else a short reason (shown nowhere, used for logs/tests)."""
    text = text_folded or ""
    if len(text) < 200:
        return ""
    lang = hint or posting_language(text)
    asks_ok_lang = _has(OK_WORDS, text)
    if lang and lang not in OK_LANGS:
        if lang == "es":
            if not asks_ok_lang:
                return "espagnol seulement"
        else:
            return f"annonce en {lang}"
    for sentence in re.split(r"[.;:!?\n•*|]+|\s-\s", text):
        if not _REQUIRED.search(sentence) or not _LANG_CTX.search(sentence) \
                or _PLUS.search(sentence):
            continue
        if _has(OTHER, sentence):
            if _has(OK_WORDS, sentence) and _CHOICE.search(sentence):
                continue  # "English or German"
            return "autre langue exigée"
        if _has(SPANISH, sentence) and not asks_ok_lang:
            return "espagnol seulement"
    return ""
