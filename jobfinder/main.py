"""Entry point: fetch offers from all sources, score, report, open in browser."""
import os
import sys
import webbrowser
from pathlib import Path

import yaml

from .matching import score_offers
from .report import write_reports, write_new_offers_summary
from .storage import mark_new
from .sources import vie, greenhouse, lever

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
GRAD_PATH = Path(__file__).resolve().parent.parent / "grad_programs.yaml"

SOURCES = [
    ("VIE (Business France)", vie),
    ("Greenhouse boards", greenhouse),
    ("Lever boards", lever),
]


def main() -> int:
    print("Loading your preferences (config.yaml)...")
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    all_offers = []
    for name, module in SOURCES:
        print(f"Fetching {name}...", end=" ", flush=True)
        try:
            found = module.fetch(config)
            print(f"{len(found)} offers")
            all_offers.extend(found)
        except Exception as exc:  # one broken source must not kill the run
            print(f"skipped ({exc})")

    print(f"\nTotal fetched: {len(all_offers)}")
    mark_new(all_offers)
    matches = score_offers(all_offers, config)

    programs = []
    if GRAD_PATH.exists():
        programs = yaml.safe_load(GRAD_PATH.read_text(encoding="utf-8")) or []

    report = write_reports(matches, programs)
    n_new = write_new_offers_summary(matches, programs)
    print(f"Matching your profile: {len(matches)} ({n_new} new)")
    print(f"\nReport saved: {report}")

    if not os.environ.get("CI"):  # on GitHub the page is published instead
        webbrowser.open(report.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
