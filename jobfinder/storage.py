"""Remember which offers were already seen (JSON file next to the code,
so it can travel with the project on GitHub)."""
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "seen_offers.json"


def mark_new(offers):
    """Set offer.is_new and persist every offer uid."""
    seen = set()
    if DB_PATH.exists():
        try:
            seen = set(json.loads(DB_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    for o in offers:
        o.is_new = o.uid not in seen
    seen.update(o.uid for o in offers)
    DB_PATH.write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")
