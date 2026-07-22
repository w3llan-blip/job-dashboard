# Job Finder — your personal offer dashboard

## Two ways to use it

**From anywhere (recommended):** once the project is on GitHub, it runs by
itself every morning (~7:00 Paris time) and publishes the results at your
personal web address — open it from any phone or computer. When new offers
appear, GitHub sends you an email notification.

**From this PC:** double-click `Find Jobs.bat` — it fetches fresh offers
right now and opens the results page in your browser.

On the results page, **NEW** = appeared since the last run. Use the filter
boxes at the top of each column (they combine), and the "New offers only"
checkbox. Click a title to open the real offer.

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

| File / folder       | What it is                                    |
|---------------------|-----------------------------------------------|
| `Find Jobs.bat`     | double-click this to search from this PC       |
| `config.yaml`       | your preferences (editable)                    |
| `docs/`             | the results page (published as your web dashboard) |
| `applications/`     | tailored CVs & cover letters (private, never uploaded) |
| `jobfinder/`        | the program code                               |
| `seen_offers.json`  | memory of offers already shown (for NEW badges) |
| `.github/`          | the daily automation schedule                  |

## Privacy note

The `.gitignore` file makes sure your CV, cover letters and the whole
`applications/` folder stay on your computer only — they are never
uploaded to GitHub.
