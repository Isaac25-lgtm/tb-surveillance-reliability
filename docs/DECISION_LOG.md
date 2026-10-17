# Decision log

| Date (UTC) | Decision | Reason |
|---|---|---|
| 2026-10-17 | Interpret "3 attempts per host" as 3 acquisition operations per host (HTTP request, or a declared git batch) | Conservative reading of investigator rule; batches listed explicitly in the attempt log |
| 2026-10-17 | Take dataset code from the official WHO data page after an empty response | Avoid guessing on the capped host |
| 2026-10-17 | Do not spend 3rd Wayback attempt; no workaround | Policy-style tunnel closures; bypassing restrictions forbidden |
| 2026-10-17 | Strict tier: all-units coverage both years, same frequency, no zero cell, base >= 50 | Frozen before any 2nd vintage (`64f3808`) |
| 2026-10-17 | Freeze 0.03 defer buffer at 10% as primary rule, no re-tuning | Prevent in-sample threshold tuning |
| 2026-10-17 | Use official WHO GTB-TME report repositories (coordinator-identified) via anonymous git; metadata-only clones plus named blobs | Lawful official archive; no broad cloning |
| 2026-10-17 | Public-by = git commit date, recorded separately from nominal snapshot date | Nominal dates are internal extraction dates, not publication |
| 2026-10-17 | Freeze retrospective comparisons (Addendum A) before computing (`8a1bd25`) | Avoid choosing comparisons after seeing outcomes |
| 2026-10-17 | Primary join requires identical frequency/coverage metadata across releases; audit all exclusions; `h1_equivalent` as labelled sensitivity | Coordinator code review; definitional changes must not masquerade as revisions |
| 2026-10-17 | Discard results of a pre-audit run unread | Produced before metadata enforcement |
| 2026-10-17 | Never load internal `remarks` free text | Contains personal names |
| 2026-10-17 | Stop advanced modelling; no hierarchical revision model, no ML | Only 2021 has repeated within-season maturities; few events |
| 2026-10-17 | Scientific status RESERVE (methods-note candidate) | 3/89 reversals at 10% (CI 0–7.6%), retrospective only, unmeasured costs |
