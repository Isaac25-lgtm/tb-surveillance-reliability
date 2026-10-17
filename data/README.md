# Data acquisition, licensing and publication boundary

| Path | Committed? | Content |
|---|---|---|
| `data/manifest/source_attempts.csv` | yes | Every acquisition attempt (successes, empty responses, blocked hosts) with URL, UTC access time, public-by basis, HTTP status, bytes, SHA-256 |
| `data/raw/who_provisional/<date>/provisional_notifications.csv` | **no** (git-ignored) | Immutable WHO provisional notification vintages |
| `data/raw/who_provisional/dictionary_<date>.csv` | no | WHO data dictionary |
| `data/manifest/gtb_tme_snapshots.csv` | yes | WHO GTB-TME archived snapshots: repo, commit, path, git blob id, bytes, SHA-256, nominal and public-by dates |
| `data/raw/gtb_tme/<repo>/<path>` | **no** (git-ignored) | Archived WHO snapshots (`.rda`/`.csv`); free-text `remarks` never loaded into outputs |

Only WHO national aggregate counts are used; there are no individual-level records. Committed outputs
are small derived aggregates (H1 totals and ratios per country-year). WHO licence terms were not
verified in this session; check WHO's terms before redistributing raw files. Synthetic test data live
only inside `tests/conftest.py` and are labelled synthetic.
