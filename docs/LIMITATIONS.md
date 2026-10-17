# Limitations

* **Retrospective, not independent.** The archived WHO snapshots are very likely the same files behind the
  earlier exploratory 5/108 result, and the 0.03 defer buffer was chosen after inspecting them. Results are a
  reproduction and sensitivity analysis, not validation.
* **Few events.** At the 10% threshold, 3 of 89 strict units changed; the country-cluster CI reaches 0. The
  balanced panel has only 4 countries.
* **Later file is not truth.** The reference (2026-10-17 public CSV) is itself a provisional file. Values for a
  year appear almost frozen after the next year's snapshot, but 2025 values are only one season old.
* **Public-by dates** are git committer dates (asserted by the committer's client), not GitHub server
  timestamps, and say nothing about earlier circulation. The 2022 repository's only commit is dated 2025.
  Earliest WHO release dates are unknown.
* **Internal vs public files.** Report-season snapshots are WHO internal extractions with the same variables as
  the public CSV; whether the public CSV on those dates had identical values is not provable here.
* **Notifications are not incidence.** No causal attribution (COVID-19, funding) is made.
* **Shrinking, selective coverage.** Countries with complete H1 fell from 117 (2021) to 67 (2025); report-season
  snapshots had complete H1 for only 34–67 countries. Reporting countries are not a random sample.
* **Maturity.** Early vintages became public 105–135 days after H1 ended; the current file had no complete H1
  2026 at 109 days. "Immediate early warning" is not supported.
* **Comparison-year revisions** (e.g. IDN 2024: base year revised down ~12%) can move ratios more than the
  current-year revision.
* **Definitions.** Strict tier excludes coverage-code changes, frequency switches, zero cells and bases < 50;
  relaxed tier and `h1_equivalent` metadata rule are labelled sensitivities.
* **Decision costs** of deferral and of misclassified alerts are not measured; only break-even ratios are reported.
