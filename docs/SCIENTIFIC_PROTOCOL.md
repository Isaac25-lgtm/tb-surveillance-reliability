# R02 scientific protocol (checkpoint 1, predeclared rules)

**Frozen:** 17 October 2026, in the commit that adds this file. The git commit timestamp on
`origin/research/r02-cloud-phase-1` is the public-by proof that the rules below were fixed
**before** any second WHO provisional vintage was obtained or inspected in this repository.
Only one vintage (`who_prov_2026-10-17`) had been seen when this was written.

## Question

When WHO provisional TB notification files are revised between public releases, how often does
a same-definition first-half (H1) year-on-year decline interpretation cross an operational alert
threshold? Does a simple precommitted defer/verify rule reduce such reversals at an acceptable
review/delay cost compared with trusting the earliest vintage?

This is about the *reliability of an interpretation of public provisional data*. It is not an
estimate of TB incidence, under-detection or causal effects (for example of funding changes or
COVID-19).

## Unit, estimand and definitions

| Item | Definition |
|---|---|
| Source | WHO Global TB Programme CSV `ds=provisional_notifications` (`m_01..m_12`, `q_1..q_4`, `report_frequency`, `report_coverage`) |
| Vintage | One downloaded file, identified by SHA-256; `public_by` = earliest *provable* public existence (our access time or an archive capture time). Never the WHO release date unless WHO documents it. |
| H1 total | Monthly rows (70): sum `m_01..m_06`, all six present. Quarterly rows (71): `q_1 + q_2`, both present. Partial sums are never used. |
| Year pair | Country c, year t: ratio r = H1(t) / H1(t-1) within one vintage. |
| Strict tier (primary) | Both H1 complete; same `report_frequency` in both years; `report_coverage` = 34 (all units) in both years; no zero H1 cell in either year; H1(t-1) >= 50. |
| Relaxed tier (sensitivity) | Both complete; same frequency; same coverage code (missing treated as its own code); H1(t-1) > 0. |
| Balanced sample | Countries with a strict pair in every year t = 2021..2025. |
| Unbalanced sample | All strict (or relaxed) pairs. |
| Alert | r <= 1 - k for k in {0.05, **0.10 (primary)**, 0.15, 0.20}; inclusive boundary. |
| Cross-vintage comparison | Same (c, t) pair, strict in an earlier vintage A and a later vintage B. B is the *later-file reference*, not truth. |
| Reversal | Alert status differs between A and B: *false early alarm* (A alert, B none) or *early miss* (A none, B alert). |
| Continuous revision | r_B - r_A and H1_B(t) / H1_A(t) - 1. |
| Maturity | Days from 30 June of year t to vintage `public_by`. |

## Predeclared defer/verification rule

* **Primary rule:** at threshold k = 0.10, defer (do not act; verify with the national programme or
  wait for the next release) when |r_A - 0.90| < **0.03**; otherwise act on vintage A.
* The 0.03 buffer is inherited from earlier *exploratory, in-sample* work and is **not re-tuned**.
  Its earlier success (all 5 reversals avoided, 17/108 deferred) is not evidence of performance.
* Sensitivity (secondary, labelled exploratory): buffers {0.01, 0.02, 0.03, 0.05} x thresholds
  {0.05, 0.10, 0.15, 0.20}.
* **Costs:** loss(trust early) = C_err x reversals; loss(defer rule) = C_err x reversals among
  acted decisions + C_def x deferrals. Reported on the cost-ratio grid C_def/C_err in
  {0.05, 0.1, 0.2, 0.3, 0.5, 1.0}, plus the break-even ratio = errors avoided / deferrals.
  The rule is only worthwhile when the real cost of a deferral (review time, delayed response)
  relative to a misclassified alert is below that break-even value. No cost value is claimed as known.

## Uncertainty and dependence

* Independent sampling unit: **country**. Pairs from the same country across years or vintage
  pairs are dependent.
* Percentile country-cluster bootstrap (2,000 resamples, seed 20261017) for proportions; report
  pairs per country. With fewer than ~20 countries, report exact counts and treat intervals as
  descriptive only.
* No hierarchical revision model unless >= 3 vintages with documented release dates and repeated
  maturities exist for the same pairs. No reporting triangle is constructed from a single file.
  No generic ML.

## Prospective design (what would count as an independent test)

The next WHO provisional vintage downloaded *after* this commit is the first uninspected later
vintage. Pairs that exist in both `who_prov_2026-10-17` and that later file are evaluated with the
rules above, unchanged. Older archived files (if lawfully obtained later) give a retrospective,
exploratory replication of the earlier 5/108 finding and must be labelled as such.

## Falsification / stop conditions

* Stop (RESERVE or methods note) if, after adequate vintages: reversals at the primary threshold
  are rare enough that the defer rule cannot beat trust-early at any plausible cost ratio; or the
  comparable sample is dominated by a handful of countries; or definition/frequency/coverage
  changes make most pairs incomparable.
* HOLD_ACCESS while fewer than two verified vintages exist.
