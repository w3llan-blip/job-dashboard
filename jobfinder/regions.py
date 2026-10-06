"""Which part of the world is an offer in?

Your rules:
- Western & Northern Europe ("west"): always OK (no visa for a French citizen)
- Southern Europe ("south"): only if the salary is shown and decent
- Eastern Europe ("east"): never
- Outside Europe ("visa"): only a VIE or an offer that says it sponsors
  the work visa
UK and Switzerland: Switzerland is "west" (free movement); the UK needs
a visa since Brexit, so it is "visa".

Locations come in many shapes ("Paris, France", "Berlin, Allemagne",
"New York -Ny-, Etats-Unis", "London, England, United Kingdom", "Remote")
so we look for country and big-city names in English and French.
Texts are accent-folded and lowercased before matching.
"""
import re

WEST = [
    "france", "germany", "allemagne", "deutschland", "netherlands", "pays-bas",
    "pays bas", "nederland", "belgium", "belgique", "luxembourg", "ireland",
    "irlande", "austria", "autriche", "switzerland", "suisse", "liechtenstein",
    "monaco", "denmark", "danemark", "sweden", "suede", "norway", "norvege",
    "finland", "finlande", "iceland", "islande",
    "paris", "ile-de-france", "lyon", "marseille", "toulouse", "lille",
    "bordeaux", "nantes", "nice", "strasbourg", "rennes", "grenoble",
    "montpellier", "berlin", "munich", "munchen", "hamburg", "frankfurt",
    "dusseldorf", "cologne", "koln", "stuttgart", "amsterdam", "rotterdam",
    "the hague", "eindhoven", "utrecht", "brussels", "bruxelles", "antwerp",
    "anvers", "ghent", "dublin", "cork", "vienna", "vienne", "wien",
    "zurich", "geneva", "geneve", "lausanne", "basel", "bale", "bern",
    "copenhagen", "copenhague", "stockholm", "gothenburg", "oslo", "helsinki",
    "reykjavik",
]
SOUTH = [
    "spain", "espagne", "espana", "italy", "italie", "italia", "portugal",
    "greece", "grece", "malta", "malte", "cyprus", "chypre", "andorra",
    "madrid", "barcelona", "barcelone", "valencia", "valence", "sevilla",
    "seville", "malaga", "bilbao", "getafe", "milan", "milano", "rome", "roma",
    "turin", "torino", "bologna", "florence", "naples", "lisbon", "lisbonne",
    "lisboa", "porto", "athens", "athenes",
]
EAST = [
    "poland", "pologne", "polska", "czech", "tchequ", "slovakia", "slovaquie",
    "hungary", "hongrie", "romania", "roumanie", "bulgaria", "bulgarie",
    "estonia", "estonie", "latvia", "lettonie", "lithuania", "lituanie",
    "croatia", "croatie", "slovenia", "slovenie", "serbia", "serbie",
    "ukraine", "belarus", "bielorussie", "moldova", "moldavie", "bosnia",
    "bosnie", "albania", "albanie", "macedonia", "macedoine", "montenegro",
    "kosovo", "russia", "russie",
    "warsaw", "varsovie", "krakow", "cracovie", "wroclaw", "gdansk", "poznan",
    "lodz", "katowice", "prague", "brno", "bratislava", "budapest", "bucharest",
    "bucarest", "voluntari", "cluj", "iasi", "timisoara", "sofia", "tallinn",
    "riga", "vilnius", "zagreb", "ljubljana", "belgrade", "kyiv", "kiev",
]
VISA = [
    "united kingdom", "royaume-uni", "royaume uni", "england", "angleterre",
    "scotland", "ecosse", "wales", "london", "londres", "manchester",
    "edinburgh", "bristol", "stevenage", "broughton", "filton", "birmingham",
    "united states", "etats-unis", "etats unis", "usa", "u.s.", "us", "nyc",
    "new york", "san francisco", "boston", "chicago", "seattle", "austin",
    "los angeles", "washington", "atlanta", "miami", "denver", "california",
    "texas", "florida", "massachusetts", "illinois", "georgia", "remote us",
    "canada", "toronto", "montreal", "vancouver", "mexico", "mexique",
    "brazil", "bresil", "sao paulo", "argentina", "argentine", "chile", "chili",
    "colombia", "colombie", "peru", "perou", "singapore", "singapour",
    "japan", "japon", "tokyo", "china", "chine", "shanghai", "beijing",
    "hong kong", "taiwan", "taipei", "korea", "coree", "seoul", "india", "inde",
    "bangalore", "bengaluru", "hyderabad", "pune", "chennai", "mumbai",
    "gurgaon", "noida", "australia", "australie", "sydney", "melbourne",
    "barangaroo", "new zealand", "nouvelle-zelande", "dubai", "emirates",
    "emirats", "saudi", "saoudite", "qatar", "israel", "turkey", "turquie",
    "morocco", "maroc", "tunisia", "tunisie", "egypt", "egypte",
    "south africa", "afrique du sud", "nigeria", "kenya", "senegal",
    "cote d'ivoire", "dominican", "dominicaine", "congo", "rwanda", "cameroun",
    "cameroon", "ghana", "algeria", "algerie", "panama", "costa rica",
    "guatemala", "cairo", "le caire", "ho chi minh", "hanoi", "bangkok",
    "jakarta", "kuala lumpur", "manila", "shenzhen", "guangzhou", "osaka",
    "abu dhabi", "riyadh", "doha", "istanbul", "casablanca", "tunis", "lagos",
    "nairobi", "johannesburg", "bogota", "lima", "santiago", "buenos aires",
    "rio de janeiro", "vietnam", "thailand", "thailande", "indonesia",
    "indonesie", "malaysia", "malaisie", "philippines",
]

# US state codes as written by many boards: "Austin, TX" / "-Ny-"
_US_STATE = re.compile(
    r"(?:,\s*|-)(?:al|ak|az|ar|ca|co|ct|dc|de|fl|ga|hi|ia|id|il|in|ks|ky|la|ma|md|"
    r"me|mi|mn|mo|ms|mt|nc|nd|ne|nh|nj|nm|nv|ny|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|va|"
    r"vt|wa|wi|wv|wy)(?:-|\s*$|\s*,)")


def _has(words, text):
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) for w in words)


def region(location_folded: str) -> str:
    """'west', 'south', 'east', 'visa' or 'unknown'.
    A multi-location posting counts as its best option (you can pick the
    Paris one in "Paris or Warsaw")."""
    loc = location_folded or ""
    if _has(WEST, loc):
        return "west"
    if _has(SOUTH, loc):
        return "south"
    if _has(EAST, loc):
        return "east"
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
