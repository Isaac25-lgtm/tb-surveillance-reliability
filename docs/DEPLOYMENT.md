# Deployment readiness (R02 results explorer)

## Verified limited deployment — 17 October 2026

Live app: https://isaac-tb-surveillance-research.streamlit.app/ . Deployed by the coordinator from reviewed `main` after PR #2 merged (`7c54f66`), Python 3.11, no secrets and **no `R02_SHOW_ARCHIVE_DERIVED` setting**. Browser verification confirmed the public-CSV overview, coverage/current-file pages and all six allowlisted download controls. CI at the reviewed head passed 34 tests.

The coordinator reviewed WHO's linked website data-policy terms (https://www.who.int/about/policies/publishing/data-policy/terms-and-conditions), which permit public-health display and derived charts with attribution. This deployment serves investigator-created aggregate analyses of the official public CSV, attributes WHO and the reporting countries, and states no endorsement; it does not redistribute or modify source files. This is a scope decision, **not a claim of CC BY licensing or permission for GitHub archive reuse**. Archive-derived panels remain withheld pending explicit reuse rights. The complete archive analysis remains available in the reviewed research code and was tested in the cloud.


**Status: HOLD_DEPLOYMENT for archive-derived results.** The current-public-file-only scope (the app's
default) is technically ready. Its public release still needs the coordinator to check the licence
points below. Nothing has been deployed from this session.

## What would be deployed

`dashboard/app.py` reads only committed aggregate files under `results/` and
`data/manifest/source_attempts.csv`. It makes no network calls, fits no models and reads no raw inputs.
It has two scopes (`dashboard/safety.py`):

| Scope | How | Content |
|---|---|---|
| `public_csv` (default) | no environment variable | Results derived only from the WHO public provisional CSV (2026-10-17): coverage, pair flow, within-file decline counts and CI, within-file figures, the source attempt log, and limitations |
| `full` | `R02_SHOW_ARCHIVE_DERIVED=1` | Adds everything derived from WHO GTB-TME GitHub internal snapshots: the vintage inventory, cross-vintage reversals, revisions, maturity, the defer rule, and their downloads |

**Downloads are allowlisted** (`safety.py`).
- Allowed: aggregate CSV tables and PNG figures only.
- Never offered: raw `.rda`/`.csv` inputs, unit-level cross-vintage ratios (`cross_vintage_units.csv`),
  per-country H1 totals (`h1_ratios_strict_*.csv`), and the free-text `remarks` field (dropped at load,
  absent from every output).

**On-screen country data.** In full scope the app does display unit-level country-year ratios: the
scatter and the changed/stable lists. These are national aggregate notification ratios, not individual
patient data, but they are derived from the internal snapshots and are covered by the hold.

## Licence audit (17 October 2026; 3 targeted requests, no 403 or authentication challenge)

| Source used | Applicable terms found | Conclusion |
|---|---|---|
| WHO provisional notifications CSV (`extranet.who.int/tme/generateCSV.asp?ds=provisional_notifications`, linked from WHO's TB data page) | WHO *Terms and conditions of use for WHO data compilations, aggregations, evaluations and analyses* (who.int/about/policies/publishing/data-policy/terms-and-conditions). See the summary below this table | **Use permitted under WHO terms**, with attribution, without WHO name/emblem or endorsement, and non-commercial. The coordinator should confirm that a derived-statistics dashboard counts as permitted use rather than an alteration needing authorisation |
| data.who.int (CC BY 4.0) | CC BY 4.0 applies to data.who.int datasets | **Not our source.** Do not label this project CC BY on that basis |
| WHO GTB-TME GitHub repositories `gtbreport2021`–`2025` (internal `monthly.rda` / `csv/monthly_*.csv` snapshots) | No LICENSE/COPYING file in any of the 5 repository roots. The 2025 README (SHA-256 `09726712…bd1fc`, 7,784 B) describes "Code and data used to develop" the report and contains no licence, copyright or reuse statement. GitHub's own terms allow viewing and forking on GitHub but grant no general reuse licence | **Unclear.** It is not established that WHO's website data terms cover files published in these repositories, and nothing grants a licence. **HOLD_DEPLOYMENT** for all archive-derived content until WHO terms for these repositories are confirmed. No permission request was sent, per instruction |

**WHO data policy terms, as they apply to the public CSV:**
- **Grant:** a royalty-free, worldwide, non-exclusive right to use, reproduce, extract, download, copy and
  distribute datasets **WHO publishes on its website**, for **public health purposes**. The terms also
  cover data derived from the datasets (tables, charts).
- **Exclusion:** datasets credited to other sources are not covered.
- **Attribution:** "WHO, title of dataset, year, date of access" plus acknowledgement of the countries
  that provided the underlying data.
- **Alterations:** only minimal style adaptation of WHO figures and tables is allowed; anything else
  needs prior written authorisation.
- **WHO name and endorsement:** no use of the WHO name or emblem, and no implied endorsement.
- **Commercial use:** no commercial promotion.
- **Warranty and copyright:** no warranty is given, and copyright remains with WHO.

**Attribution used in the app and README:** "Data: World Health Organization, Global Tuberculosis
Programme — provisional TB notifications (accessed 2026-10-17); underlying data reported by countries
and territories to WHO. Analysis created by the investigator; not a WHO product; no WHO endorsement."

The app shows no WHO emblem.

## Technical readiness evidence (this session)

- **Pinned dependencies:** `requirements.txt` pins streamlit 1.66.0, altair 6.3.0, pandas 3.0.6 and
  numpy 2.4.6. These are what the app imports.
  - numpy 2.5.x has no Python 3.11 wheel, so the pin is 2.4.6. The analysis environment used 2.5.4 on
    Python 3.13.
  - In a clean **Python 3.11.17** venv with exactly these pins (plus pytest 9.1.1), the dashboard and
    integrity tests passed. With the package installed, the full suite passed: 34 passed (after the presentation-consistency fix; 29 before it).
- **CI:** runs on Python 3.11 and installs `requirements.txt` plus the package.
- **Streamlit config:** `.streamlit/config.toml` runs headless, collects no usage stats, hides error
  details from viewers, sets a light theme and disables the file watcher.
- **Credentials:** none needed. There are no secrets and no `secrets.toml`.
- **Main file path:** `dashboard/app.py`. The repository root must be deployed, because the app reads
  `results/`, `docs/` and `src/tbvintage`.

## Deployment blockers / coordinator checklist

1. **Licence (blocking for full scope).** Confirm the WHO terms covering the GTB-TME GitHub snapshots.
   Until then deploy only the default scope, and do not set `R02_SHOW_ARCHIVE_DERIVED`.
2. **Licence (default scope).** Confirm that public display of investigator-derived statistics from the
   WHO public CSV, with attribution, is acceptable under the WHO data policy's public-health-purpose and
   alteration clauses.
3. **Scientific labelling.** The decision is RESERVE and the analysis is retrospective and exploratory.
   The app states this on every page. Keep `docs/STATUS.md` as the source of the decision label.
4. **Not verified here.** Streamlit Community Cloud build and rendering. The app has only been run with
   Streamlit's AppTest in this container, not served to a browser.
