"""Entry point: fetch offers from all sources, score, report, open in browser."""
import os
import sys
import webbrowser
from pathlib import Path

import yaml

from .matching import score_offers, LAST_DROPS
from .report import write_reports, write_new_offers_summary
from .storage import mark_new
from .sources import vie, greenhouse, lever, ashby, workday, wttj, francetravail, linkedin

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
GRAD_PATH = Path(__file__).resolve().parent.parent / "grad_programs.yaml"

SOURCES = [   # (name shown in logs, module, label used on offers)
    ("VIE (Business France)", vie, "VIE"),
    ("Greenhouse boards", greenhouse, "Greenhouse"),
    ("Lever boards", lever, "Lever"),
    ("Ashby boards", ashby, "Ashby"),
    ("Workday (large groups)", workday, "Workday"),
    ("Welcome to the Jungle", wttj, "WTTJ"),
    ("France Travail", francetravail, "France Travail"),
    ("LinkedIn public search", linkedin, "LinkedIn"),
]


def main() -> int:
    print("Loading your preferences (config.yaml)...")
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    all_offers = []
    health = []   # (source, label, fetched count or None, error) — shown on the page
    for name, module, label in SOURCES:
        print(f"Fetching {name}...", end=" ", flush=True)
        try:
            found = module.fetch(config)
            print(f"{len(found)} offers")
            all_offers.extend(found)
            health.append((name, label, len(found), ""))
        except Exception as exc:  # one broken source must not kill the run
            print(f"skipped ({exc})")
            health.append((name, label, None, str(exc)[:120]))

    # drop cross-source duplicates (e.g. LinkedIn repeating a company's
    # own job board) — direct sources are listed first, so they win
    unique, seen_keys = [], set()
    for o in all_offers:
        key = (o.title.strip().lower(), o.company.strip().lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(o)
    all_offers = unique

    print(f"\nTotal fetched (after dedup): {len(all_offers)}")
    mark_new(all_offers)
    matches = score_offers(all_offers, config)
    kept_by_source = {}
    for o in matches:
        kept_by_source[o.source] = kept_by_source.get(o.source, 0) + 1

    programs = []
    if GRAD_PATH.exists():
        programs = yaml.safe_load(GRAD_PATH.read_text(encoding="utf-8")) or []

    report = write_reports(matches, programs, health, kept_by_source, dict(LAST_DROPS))
    n_new = write_new_offers_summary(matches, programs)
    print(f"Matching your profile: {len(matches)} ({n_new} new)")
    print(f"\nReport saved: {report}")

    if not os.environ.get("CI"):  # on GitHub the page is published instead
        webbrowser.open(report.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
