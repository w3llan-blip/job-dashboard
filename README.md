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
small bonus.

**Where:** Western & Northern Europe always; Southern Europe (Spain,
Italy, Portugal, Greece...) only if a decent salary is shown (thresholds
in `salary:`; VIEs always pass); Eastern Europe never; outside Europe
only VIEs or offers that say they sponsor the visa (**VISA ✓** badge).

**Languages:** offers asking for a language other than French/English
(Spanish only as an extra), or written in another language, are removed
(`languages.enabled`). Marketing roles are excluded (`keywords.exclude`).

**Ranking:** every offer gets a score out of 100 — role (35, your core
roles are in `keywords.priority`), level/contract (20: VIE, graduate,
internship, junior; minus points if 3+ years of experience are asked),
start date (10), company size (10), location (10), salary shown (8),
freshness (7), bonus words (5). Open "Détails" on an offer to see why it
got its score. The "Sources" tab also lists how many offers each filter
removed.

## Sorting offers on the dashboard

Each offer has three buttons:

- **☆** keeps it for later (**★ Gardées** tab)
- **✓ Postulé** moves it to **✓ Candidatures**: a compact tracker with
  the application date, a status (Postulé, Relancé, Entretien, Test,
  Offre, Refusé) and a notes field. After 10 days with no news it shows
  "À relancer". The offer stays there even once it's gone from the site.
- **✕ Pas intéressé** hides it (**Masquées** tab, where you can restore it)

Every action can be undone for 5 seconds ("Annuler"). Quick filters
(VIE, Stage, Graduate, Europe, Visa sponsorisé...) combine with the
search box. Keyboard: J/K to move, A applied, X not interested,
S keep, O open, / search.

Your choices are saved **in the browser** you use (they survive the
daily update). To carry them to another device, use **Exporter** at the
bottom of the page, then **Importer** on the other one. The online
dashboard and the local `Find Jobs.bat` page don't share choices.

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
