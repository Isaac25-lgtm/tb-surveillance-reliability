# Data access: fetched vs catalogued

| Source | Status | Licence / terms | Notes |
|---|---|---|---|
| WHO provisional TB notifications CSV (current) | **Fetched** 2026-10-17, hash-verified | WHO website terms; licence text not verified in this session | Raw file git-ignored under `data/raw/`; re-fetch with `scripts/acquire.py` (a re-fetch is a new vintage) |
| WHO TB data dictionary CSV | **Fetched** 2026-10-17 | as above | Code definitions 70/71 (frequency), 34/35 (coverage) |
| WHO GTB-TME report repositories `gtbreport2021`–`gtbreport2025` (official WHO Global TB Programme GitHub) | **Fetched** 2026-10-17 via anonymous git: commit/tree metadata plus 17 named blobs; hashes in `data/manifest/gtb_tme_snapshots.csv` | Repository licence files not reviewed in this session; check before redistributing raw files | 15 distinct archived vintages (nominal 2021-06-29 to 2025-07-30). Public-by = git committer date (client-asserted) |
| Internet Archive copies of the CSV | **Blocked** by this environment's network policy | — | No longer needed for the retrospective analysis |
| Prior Feasibility Lab files (Windows `F:` path / handoff ZIP) | **Not accessible** from cloud | — | — |
| WHO annual case notifications (`ds=notifications`) | Catalogued only | — | Not fetched (WHO host attempt cap); different definition |

A file counts as a vintage only if its SHA-256 matches the manifest and the config. Internal snapshots
are loaded without their free-text `remarks` column, which can name individuals; it is never written to
outputs.
