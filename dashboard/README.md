# R02 results explorer

`streamlit run dashboard/app.py` starts a read-only explorer. It reads only the committed aggregate
files in `results/` plus `data/manifest/source_attempts.csv`. It makes no network calls, reads no raw
data, and fits no models.

**Scope.** Set in `safety.py`:
- *Default:* shows only results derived from the WHO public provisional CSV.
- *Full:* `R02_SHOW_ARCHIVE_DERIVED=1` adds results derived from the WHO GTB-TME GitHub snapshots, whose
  reuse terms are unconfirmed (`docs/DEPLOYMENT.md`).

**Pages:**
- Overview
- Sources and vintages: nominal snapshot dates vs git committer dates
- Coverage and exclusions
- Within current file
- *Full scope only:* Alert reversals, with analysis, tier, metadata rule, sample, threshold, year and
  country filters; changed and stable lists; and clustered-CI comparison
- *Full scope only:* Revision distributions
- *Full scope only:* Maturity
- *Full scope only:* Defer rule, by threshold, buffer and cost ratio
- Downloads: allowlisted aggregate CSV and PNG files only
- Limitations and licensing

**Tests.** `tests/test_dashboard.py` renders every page in both scopes, exercises the filters, and
checks the download allowlist. Deployment pins are in `requirements.txt` (Python 3.11).

**Status.** Not deployed; see `docs/DEPLOYMENT.md` for the blockers.
