# R02 evidence status (17 October 2026, cloud session)

## Decision

| Dimension | Status |
|---|---|
| Data access | **Resolved for retrospective work.** 15 distinct archived official WHO vintages from the GTB-TME annual-report GitHub repositories (2021–2025), plus the current public CSV. The Internet Archive is still blocked here, but it is no longer needed. |
| Method validity | Same-definition H1 pairs. Reporting metadata must be identical across releases, and every exclusion is audited. Uncertainty comes from a country-cluster bootstrap. Adversarial tests cover metadata changes between releases. |
| Scientific novelty | Modest. Revisions are known. What is new is a decision-level measure, and it shows few reversals. |
| AI incremental value | Not applicable. Advanced modelling was **stopped**: there are too few repeated maturities per year for a revision model, and no ML was fitted. |
| Overall | **RESERVE**, candidate for a short methods note. This is retrospective and exploratory, not independent validation. |

## Main result (C1, primary; retrospective)

**Design.** The early vintage is the WHO report-season snapshot for year t. The reference is the
2026-10-17 public CSV. Each unit is one country's H1(t)/H1(t−1) ratio. It must be strict in both
files with identical frequency and coverage metadata. The design was frozen at `8a1bd25` before
computation (see `docs/SCIENTIFIC_PROTOCOL.md`, Addendum A).

| | Value |
|---|---|
| Units / countries | **89 / 52** (at most 4 per country). By year: 2021 26, 2023 15, 2024 18, 2025 30 |
| Public-by lag of the early vintage after H1 end | 105, 130, 121 and 135 days (git commit dates) |
| Alert status changed at 5 / **10** / 15 / 20 % | 5 / **3** / 2 / 1 |
| Share changed at 10 % (country-cluster 95 % CI) | **3.4 % (0–7.6 %)**. All 3 were false early alarms (MYS 2021, TZA 2023, IDN 2024); no early misses |
| Share changed at 5 / 15 / 20 % | 5.6 % (1.3–10.3) / 2.2 % (0–5.4) / 1.1 % (0–3.8) |
| Mean absolute ratio revision | 0.018 (0.011–0.025). Median absolute revision 0.001; 90th percentile 0.056 |
| H1(t) total unchanged / revised up | 43.8 % / 34.8 % of units |
| Balanced panel (all 4 years) | 4 countries, 16 units, 0 changed at 10 % (descriptive only) |

**Predeclared defer rule** (k = 0.10, buffer 0.03; the buffer came from earlier exploratory work on
overlapping data):
- It defers **14 of 89** decisions and removes all 3 reversals.
- Break-even ratio = errors avoided ÷ deferrals = 3/14 = **0.21**. The rule is worthwhile only if one
  deferral (verification, delay) costs less than about a fifth of one misclassified alert.
- Buffers 0.01, 0.02 and 0.05 defer 7, 11 and 25 decisions and leave 2, 0 and 0 reversals.

The rule's real costs are not measured here.

**Sensitivity analyses**
- *Relaxed tier:* 125 units from 76 countries; 8 changed at 10 % (6.4 %, CI 2.4–11.8 %; 6 false
  alarms, 2 misses).
- *`h1_equivalent` metadata rule:* identical to the primary, because no included unit changed
  frequency or coverage between releases.
- *S1, the 2022 group* (git public-by 999 days after H1): 30 units, 0 changed at 10 %.
- *S3, next-report reference:* 89 units, 3 changed.
- *IDN 2024:* the ratio moved by +0.171 although H1 2024 itself rose only 4.7 %. That arithmetic
  implies the 2023 base was revised down by about 12 %. Revisions to the comparison year matter.

**Maturity.** Values for year t are revised between the year-t and year-(t+1) report snapshots: 102
of 114, 68 of 92 and 62 of 92 rows differ. After that they are almost frozen: 0–4 rows differ against
the 2026 file. In the nine 2021 internal snapshots (S4), the strict H1-2021 units comparable to the
reference rose from 1 (nominal 29 Jun) to 8 (28 Jul), 20 (11 Aug) and 26 (8 Oct). These snapshots
became public only on 13 Oct 2021.

**Comparison with the earlier exploratory claim** (5/108 at 10 %, 64 countries, 103 stable, 17 deferred):
- *Not reproduced exactly.* This audited strict design gives 3/89 from 52 countries, with 86 stable
  and 14 deferred. The relaxed tier gives 8/125 from 76 countries.
- The source repositories and the 105–135-day lags match. The earlier definitions are unknown, so
  the gap is not explained.
- Both analyses agree on the order of magnitude: about 3–6 % of 10 % alerts change.

## Sources (exact)

**Attempt log** (`data/manifest/source_attempts.csv`):
- *extranet.who.int (3 attempts):* one empty response (wrong dataset code), then the current
  provisional CSV (56,347 B, `a4be40a0…`, 647 rows) and the data dictionary.
- *web.archive.org (2 attempts):* both blocked by the environment's network policy.
- *github.com git (3 batch operations):*
  1. a metadata-only clone of `GTB-TME/gtbreport2024`;
  2. `ls-remote` plus metadata-only clones of 2021, 2022, 2023 and 2025;
  3. a fetch of 17 blobs.

**Archived snapshots** (`data/manifest/gtb_tme_snapshots.csv`):
- 17 files carry git blob ids, bytes, SHA-256, nominal snapshot dates and commit dates.
- Two `.rda` files duplicate CSV content, leaving 15 distinct vintages.
- The 2024 snapshot `.rda` is 26,984 B, as the coordinator reported.
- The `gtbreport2022` repository has one commit, dated 2025-03-25. An earlier public release of the
  2022 snapshot cannot be proven here.

## Within-vintage audit of the 2026-10-17 file (unchanged from checkpoint 1)

- **Complete H1 coverage:** 117 countries (2021), 108, 83, 80, 67 (2025) and **0 for 2026** (only January
  is reported, by 7 countries).
- **Pairs:** 200 strict pairs from 76 countries. Of these, 31/200 (15.5 %, CI 11.2–20.2 %) show an
  H1 decline of 10 % or more. That is year-on-year change, not revision reliability.

## Commands and tests

- **Tests:** `pytest -q` → 20 passed.
- **Pipeline:** `scripts/run_pipeline.py` at `c2004a9` took 3 min 33 s on 1 thread.
- **Reproducibility:** the reference-vintage tables are byte-identical to the checkpoint-1 outputs.
- **CI** runs on pull requests only.

See `docs/REPRODUCIBILITY.md`.

## Next decision

A methods note is defensible. It would cover how often public WHO provisional H1 alerts reverse
after same-definition matching, the maturity lag, and the cost threshold above which deferral does
not pay. A full original article is not supported: there are few reversals, CIs reach zero, the rule
is not independently validated, and decision costs are unknown.

The only independent test available is prospective. Apply the frozen rule unchanged to the next WHO
report snapshot (the year-2026 H1 values, when published) and judge it against the following year's
file.
