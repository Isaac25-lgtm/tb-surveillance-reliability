# Data access: fetched vs catalogued

| Source | Status | Licence / terms | Notes |
|---|---|---|---|
| WHO provisional TB notifications CSV (current) | **Fetched** 2026-10-17, hash-verified | WHO website terms; licence text not verified in this session | Raw file git-ignored under `data/raw/`; re-fetch with `scripts/acquire.py` |
| WHO TB data dictionary CSV | **Fetched** 2026-10-17 | as above | Only the provisional-notification code definitions are used |
| Archived copies of the provisional CSV (Internet Archive) | **Blocked** by this environment's network policy | Internet Archive terms | Needs the environment's allowed domains to include `web.archive.org`, or investigator-supplied files with capture metadata |
| Prior Feasibility Lab vintages (Windows `F:` path / handoff ZIP) | **Not accessible** from cloud | — | Not searched beyond confirming absence in the repository |
| WHO annual case notifications (`ds=notifications`) | Catalogued only | — | Not fetched: WHO host attempt cap reached; would allow provisional-vs-annual comparison (different definition) |

A file counts as a vintage only if registered with `outcome=ok` in `data/manifest/source_attempts.csv`
and its SHA-256 matches. `public_by` is the earliest provable public existence, not WHO's release date.
