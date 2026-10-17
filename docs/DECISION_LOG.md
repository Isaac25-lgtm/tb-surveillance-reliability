# Decision log

| Date (UTC) | Decision | Reason |
|---|---|---|
| 2026-10-17 | Interpret "3 attempts per host" as 3 HTTP acquisition requests per host | Conservative reading of investigator rule |
| 2026-10-17 | Take dataset code from the official WHO data page after an empty response | Avoid guessing on the capped host |
| 2026-10-17 | Do not spend 3rd Wayback attempt; no workaround (e.g. fetch tools outside the proxy) | Two identical policy-style tunnel closures; investigator forbids bypassing restrictions |
| 2026-10-17 | Strict tier: all-units coverage both years, same frequency, no zero cell, base >= 50 | Zero cells and tiny bases make ratios unstable; frozen before any 2nd vintage |
| 2026-10-17 | Freeze 0.03 defer buffer at 10% as primary rule, no re-tuning | Prevent in-sample threshold tuning |
| 2026-10-17 | Stop advanced modelling; no hierarchical revision model, no ML | One vintage; H1 2026 maturity insufficient |
| 2026-10-17 | Scientific status HOLD_ACCESS | Cross-vintage estimand not estimable |
