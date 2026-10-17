# Are TB notification decline alerts stable across WHO public data vintages?

Investigator: Isaac Omoding · Research programme R02 · Stage: **retrospective analysis complete, decision RESERVE (methods-note candidate)**

WHO publishes provisional monthly and quarterly TB notifications so that falls in case finding can be
spotted quickly. These files are revised as countries update them. If a programme or funder reads
"notifications fell by at least 10% in the first half-year" from one release, how often would a later
release reverse that reading, and would a simple precommitted "verify before acting" rule be worth its
cost? Notifications are not incidence, and nothing here attributes changes to any cause.

## Research questions

1. After matching period, reporting frequency and coverage definition, how often do first-half (H1)
   year-on-year decline alerts at 5/10/15/20% change between WHO provisional vintages?
2. How large are continuous revisions to H1 ratios, and how do they depend on maturity and country?
3. Does a predeclared defer/verify rule (defer when the early ratio is within 0.03 of the 10% cut-off)
   reduce reversals at an acceptable deferral cost, judged on an uninspected later vintage?

## What is known and what is not claimed

WHO states that these data are provisional (Global TB Reports 2021–2022; Falzon et al., *Front Immunol*
2023, doi:10.3389/fimmu.2023.1234785), and reporting-delay nowcasting is well developed
(Höhle & an der Heiden, *Biometrics* 2014, doi:10.1111/biom.12194). This project would add a
*decision-level* measure: how often alerts reverse across public releases. See
[docs/PRIOR_ART.md](docs/PRIOR_ART.md). An earlier exploratory analysis reported 5 of 108 alerts
changed at the 10% threshold. This repository did **not** reproduce that count exactly, but finds the same
order of magnitude (below).

## Data and current access

| Source | Coverage | Status |
|---|---|---|
| WHO `provisional_notifications` CSV, vintage 2026-10-17 (56,347 B, SHA-256 `a4be40a0…84aa8630d29e4c52afb35e6735a8b312032d4fb8cd684b`) | 142 countries, 2020–2026 | fetched, hash-verified |
| WHO Global TB Programme report repositories `GTB-TME/gtbreport2021`–`2025` | 15 distinct archived snapshots, nominal 2021-06-29 to 2025-07-30 | fetched by git (17 blobs, hashes and commit dates in [data/manifest/gtb_tme_snapshots.csv](data/manifest/gtb_tme_snapshots.csv)) |
| Internet Archive copies | — | blocked by this cloud environment; not needed |

Every attempt, including failures, is in [data/manifest/source_attempts.csv](data/manifest/source_attempts.csv).
"Public-by" dates are git commit dates (105–135 days after H1 ended for the 2021/2023/2024/2025 report
snapshots), not proven WHO release dates.

## Results (retrospective and exploratory)

Primary comparison C1: the WHO report-season snapshot for year t against the 2026-10-17 public file. Each unit
is a country's H1(t)/H1(t−1) ratio, same-definition in both files, with identical frequency and coverage
metadata across releases. Design frozen before computation.

* **89 units from 52 countries** (2021, 2023, 2024, 2025). At the **10% decline threshold, 3 alerts changed
  (3.4%; country-cluster 95% CI 0–7.6%)**, all false early alarms. Thresholds 5/15/20%: 5/2/1 changed.
* Revisions are mostly small. Median absolute ratio change is 0.001 and the 90th percentile is 0.056. Revisions
  to the comparison year can matter: in IDN 2024 the 2023 base implicitly fell about 12%.
* **Predeclared defer rule** (verify when within 0.03 of the cut-off) deferred 14/89 decisions and removed all
  3 reversals. It pays off only if a deferral costs less than about **0.21** of a misclassified alert. This is
  retrospective, and the buffer came from earlier exploration of overlapping data, so it is not validation.
* Relaxed definitions give 8/125 changed (6.4%, CI 2.4–11.8%).
* A year's values are revised until the next year's report snapshot, then barely change.

![Early vs reference ratios](results/figures/c1_revision_scatter.png)

![Defer trade-off](results/figures/c1_defer_tradeoff.png)

The current public file's own coverage keeps thinning: complete H1 fell from 117 countries in 2021 to 67 in
2025, and there were none for 2026 at 109 days after H1 ended.

![Coverage by year](results/figures/coverage_who_prov_2026-10-17.png)

Full numbers: [docs/STATUS.md](docs/STATUS.md) · tables: [results/](results/README.md).

## Design

Raw WHO file → H1 totals (six months or two quarters, never partial) → strict / relaxed same-definition
pairs → cross-vintage join that requires identical reporting metadata, with every exclusion audited →
threshold reversals against a later file (a reference, not the truth) → predeclared defer rule on a cost-ratio
grid → country-cluster bootstrap. No reporting triangle is built and no ML is fitted, because there are too few
repeated maturities. Protocol and Addendum A (each frozen before the corresponding computation):
[docs/SCIENTIFIC_PROTOCOL.md](docs/SCIENTIFIC_PROTOCOL.md).

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[test,dashboard,archives]"
python scripts/acquire.py            # one request; a new date is a new vintage
# archived WHO snapshots: git commands in docs/REPRODUCIBILITY.md
python scripts/run_pipeline.py       # needs the hash-matching raw files listed in configs/experiment.yaml
pytest -q                            # synthetic fixtures + committed aggregates
streamlit run dashboard/app.py       # local aggregate explorer, not deployed
```

Details: [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Risks and next step

The effect is small: few reversals, CIs that reach zero, a balanced panel of only 4 countries, and decision
costs that are not measured. That supports a short methods note at most, not a full original article. The
only independent test is prospective: apply the frozen rule unchanged to the next WHO report snapshot and
judge it against the following year's file. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) and
[docs/DECISION_LOG.md](docs/DECISION_LOG.md).

## Acknowledgements and disclosure

Data: WHO Global Tuberculosis Programme. Code, analysis and documentation in this checkpoint were
produced with AI assistance (Claude Code) under the investigator's direction and need human review.
Operating contract: [AGENTS.md](AGENTS.md).
