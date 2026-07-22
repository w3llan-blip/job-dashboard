# Job Finder — your personal offer dashboard

## How to use (2 steps)

1. **Double-click `Find Jobs.bat`** — it fetches fresh offers, filters them
   for you, and opens a results page in your browser.
2. Browse the page. **NEW** = appeared since your last run.
   Click a title to open the real offer.

Run it as often as you like (every morning is a good habit).

## Where offers come from

- **VIE / VIA** — the official Business France site (your priority)
- **Greenhouse & Lever** — the public job boards of ~30 tech companies
  (Datadog, Stripe, Spotify, Doctolib, Back Market, Qonto, Figma...)

## Tune your results

Open `config.yaml` (right-click → Open with Notepad) and edit:

- `keywords.include` — words a job title must contain
- `keywords.exclude` — words that remove an offer (tech roles)
- `keywords.boost` — words that push an offer up the ranking
- `locations.preferred` — places that get bonus points
- `companies` — add/remove companies to watch

Save the file and re-run `Find Jobs.bat`.

## Applying to an offer

When you find an offer you like, come back to Kiro and say for example:

> "Prepare an application for this offer: <paste the offer link>"

Kiro will read the offer, tailor your CV and cover letter to it, and save
them in the `applications/` folder — then you review and send them yourself.

## Files in this folder

| File / folder      | What it is                                    |
|--------------------|-----------------------------------------------|
| `Find Jobs.bat`    | double-click this to search                    |
| `config.yaml`      | your preferences (editable)                    |
| `results/`         | the offer list (HTML page + Excel-compatible CSV) |
| `applications/`    | tailored CVs & cover letters, one folder per offer |
| `jobfinder/`       | the program code                               |
| `seen_offers.db`   | memory of offers already shown (for NEW badges) |
