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
- **Greenhouse, Lever & Ashby** — the public job boards of tech scale-ups
  (Datadog, Stripe, Spotify, Doctolib, Back Market, Qonto, Figma...)
- **Workday** — the career sites of large groups (Sanofi, Airbus,
  Michelin, Pernod Ricard...). Add more under `workday:` in `config.yaml`.
- **Welcome to the Jungle** — searches listed in `config.yaml`;
  companies under 200 people are dropped (`company_size`), so you get
  scale-ups and large groups, not early startups.
- **France Travail** — the official public-employment API (optional,
  needs a free key, see below)
- **LinkedIn** — public search (often blocked from GitHub's servers)

At the bottom of the dashboard, **Sources today** shows how many offers
each source returned and how many passed your filters. A source stuck
at 0 is blocked or misconfigured.

Offers that don't state a start date are kept with a **DATE ?** badge
(companies rarely write it); offers whose date fits your window get a
small bonus. Offers that say they won't sponsor a visa are removed.

## Turning on France Travail (optional, 10 minutes)

1. Create an account on https://francetravail.io
2. Create an application and subscribe it to the **Offres d'emploi** API
3. On GitHub: your repo → Settings → Secrets and variables → Actions →
   add `FT_CLIENT_ID` and `FT_CLIENT_SECRET` with the values shown there.

Without the key, that source is simply skipped.

## Tune your results

Open `config.yaml` (right-click → Open with Notepad) and edit:

- `keywords.include` — words a job title must contain
- `keywords.exclude` — words that remove an offer (tech roles)
- `keywords.boost` — words that push an offer up the ranking
- `locations.preferred` — places that get bonus points
- `companies` — add/remove companies to watch
- `workday` — large groups' career sites to watch
- `welcome_to_the_jungle.queries` / `france_travail.queries` — searches to run
- `company_size.min_employees` — minimum company size (default 200)

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
| `org_sizes.json`    | cached company sizes from Welcome to the Jungle |
| `.github/`          | the daily automation schedule                  |

## Privacy note

The `.gitignore` file makes sure your CV, cover letters and the whole
`applications/` folder stay on your computer only — they are never
uploaded to GitHub.
