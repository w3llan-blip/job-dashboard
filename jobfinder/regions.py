"""Where can you work without a visa?

As a French citizen you can work (and do a 6-month end-of-studies
internship) anywhere in the EU/EEA and Switzerland. Outside, you need a
work visa: those offers are only interesting if they are a VIE (visa
handled by Business France) or if they say they sponsor the visa.

Locations come in many shapes ("Paris, France", "Berlin, Allemagne",
"New York -Ny-, Etats-Unis", "London, England, United Kingdom", "Remote")
so we look for country and big-city names in English and French.
Texts are accent-folded and lowercased before matching.
"""
import re

# EU + EEA + Switzerland: no visa needed
FREE = [
    "france", "germany", "allemagne", "deutschland", "netherlands", "pays-bas",
    "pays bas", "belgium", "belgique", "spain", "espagne", "italy", "italie",
    "portugal", "luxembourg", "ireland", "irlande", "denmark", "danemark",
    "sweden", "suede", "finland", "finlande", "austria", "autriche", "poland",
    "pologne", "czech", "tchequ", "slovakia", "slovaquie", "slovenia",
    "slovenie", "hungary", "hongrie", "romania", "roumanie", "bulgaria",
    "bulgarie", "greece", "grece", "croatia", "croatie", "estonia", "estonie",
    "latvia", "lettonie", "lithuania", "lituanie", "malta", "malte", "cyprus",
    "chypre", "norway", "norvege", "iceland", "islande", "liechtenstein",
    "switzerland", "suisse", "monaco",
    # cities commonly written without a country
    "paris", "lyon", "marseille", "toulouse", "lille", "bordeaux", "nantes",
    "berlin", "munich", "hamburg", "frankfurt", "amsterdam", "rotterdam",
    "brussels", "bruxelles", "madrid", "barcelona", "barcelone", "milan",
    "rome", "lisbon", "lisbonne", "dublin", "copenhagen", "stockholm",
    "vienna", "vienne", "warsaw", "varsovie", "prague", "zurich", "geneva",
    "geneve", "lausanne", "basel", "oslo", "helsinki", "emea", "europe",
]

# Outside the EU/EEA/CH: visa needed
VISA = [
    "united kingdom", "royaume-uni", "royaume uni", "england", "angleterre",
    "scotland", "ecosse", "wales", "london", "londres", "manchester",
    "edinburgh", "united states", "etats-unis", "etats unis", "usa", "u.s.",
    "new york", "san francisco", "boston", "chicago", "seattle", "austin",
    "los angeles", "washington", "atlanta", "miami", "denver",
    "canada", "toronto", "montreal", "vancouver", "mexico", "mexique",
    "brazil", "bresil", "sao paulo", "argentina", "argentine", "chile", "chili",
    "colombia", "colombie", "peru", "perou", "singapore", "singapour",
    "japan", "japon", "tokyo", "china", "chine", "shanghai", "beijing",
    "hong kong", "taiwan", "taipei", "korea", "coree", "seoul", "india", "inde",
    "bangalore", "mumbai", "australia", "australie", "sydney", "melbourne",
    "new zealand", "nouvelle-zelande", "dubai", "emirates", "emirats",
    "saudi", "saoudite", "qatar", "israel", "turkey", "turquie", "morocco",
    "maroc", "tunisia", "tunisie", "egypt", "egypte", "south africa",
    "afrique du sud", "nigeria", "kenya", "senegal", "cote d'ivoire",
    "dominican", "dominicaine", "congo", "rwanda", "cameroun", "cameroon",
    "ghana", "algeria", "algerie", "panama", "costa rica", "guatemala",
    "cairo", "le caire", "ho chi minh", "hanoi", "bangkok", "jakarta",
    "kuala lumpur", "manila", "shenzhen", "guangzhou", "osaka", "abu dhabi",
    "riyadh", "doha", "istanbul", "casablanca", "tunis", "lagos", "nairobi",
    "johannesburg", "bogota", "lima", "santiago", "buenos aires", "rio de janeiro",
    "vietnam", "thailand", "thailande", "indonesia", "indonesie", "malaysia",
    "malaisie", "philippines", "ukraine", "serbia", "serbie",
]

# US state codes as written by many boards: "Austin, TX" / "-Ny-"
_US_STATE = re.compile(
    r"(?:,\s*|-)(?:al|ak|az|ar|ca|co|ct|dc|de|fl|ga|hi|ia|id|il|in|ks|ky|la|ma|md|"
    r"me|mi|mn|mo|ms|mt|nc|nd|ne|nh|nj|nm|nv|ny|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|va|"
    r"vt|wa|wi|wv|wy)(?:-|\s*$|\s*,)")


def _has(words, text):
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) for w in words)


def region(location_folded: str) -> str:
    """'free' (EU/EEA/CH), 'visa' (elsewhere) or 'unknown'.
    If a location lists both (multi-location posting), it counts as free:
    you can take the EU one."""
    loc = location_folded or ""
    if _has(FREE, loc):
        return "free"
    if _has(VISA, loc) or _US_STATE.search(loc):
        return "visa"
    return "unknown"


# The offer says it DOES sponsor (negative phrasings were already removed
# by the disqualifiers in config.yaml before this check runs).
_SPONSOR_OK = [re.compile(p) for p in (
    r"visa sponsorship (?:is |will be |can be )?(?:available|provided|offered|possible)",
    r"(?:offer|offers|provide|provides|including|includes|with) (?:full )?visa sponsorship",
    r"(?:we|will|can|able to|happy to) (?:\w+ ){0,2}sponsor (?:your |a |the |work )?(?:visa|work permit|work authori[sz]ation)",
    r"sponsorship (?:is )?(?:available|provided|offered)",
    r"relocation (?:and|&) visa (?:support|assistance|sponsorship)",
    r"visa (?:support|assistance) (?:is )?(?:available|provided|offered)",
    r"(?:open to|considers?|welcome) (?:candidates|applicants) (?:\w+ ){0,3}requiring (?:visa )?sponsorship",
    r"(?:prise en charge|accompagnement) (?:du |de |des )?(?:visa|permis de travail)",
    r"parrainage (?:de |du )?visa",
)]


def sponsors_visa(description_folded: str) -> bool:
    return any(p.search(description_folded or "") for p in _SPONSOR_OK)
