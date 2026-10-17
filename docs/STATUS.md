# R02 evidence status — checkpoint 1 (17 October 2026, cloud session)

## Decision

| Dimension | Status |
|---|---|
| Data access | **HOLD_ACCESS** — current WHO vintage fetched; archived vintages blocked (web.archive.org denied by this environment's network policy) |
| Method validity | Pipeline, definitions and predeclared defer rule implemented and unit-tested; cross-vintage estimand not yet estimable |
| Scientific novelty | Unresolved; bounded search found no published quantification of threshold reversals across WHO provisional releases (not proof of absence) |
| AI incremental value | Not applicable; advanced modelling **stopped** (insufficient vintages/maturity) |
| Readiness | Not a manuscript. Overall: **HOLD_ACCESS** (fallback RESERVE if no archived vintages can be lawfully obtained) |

## Environment probe

Linux cloud container, Python 3.13.16 (venv; package targets >= 3.11), 4 vCPU (computations limited to
2 threads), 15 GiB RAM, ~31 GB free disk, root, pip install permitted, HTTPS via agent proxy.
`extranet.who.int` reachable; `web.archive.org` blocked (tunnel closed after 39 bytes, twice).
No access to the investigator's Windows `F:` path or earlier handoff ZIPs. Billing not readable from
this session.

## Sources (exact)

| # | Host | URL | Result | Bytes | SHA-256 |
|---|---|---|---|---|---|
| 1 | extranet.who.int | `generateCSV.asp?ds=c_newinc_prov` | HTTP 200, empty (wrong dataset code guessed) | 0 | — |
| 2 | extranet.who.int | `generateCSV.asp?ds=provisional_notifications` | **OK**, server filename `TB_provisional_notifications_2026-10-17.csv`, 647 rows x 24 cols, 142 countries, 2020–2026 | 56,347 | `a4be40a0d977a47e7684aa8630d29e4c52afb35e6735a8b312032d4fb8cd684b` |
| 3 | extranet.who.int | `generateCSV.asp?ds=dictionary` | **OK** (defines codes 70/71, 34/35) | 108,122 | `2b0aecd442bffabf2f313d2eaa478ffaea48d09fe78670a136a1956c042011bf` |
| 1 | web.archive.org | CDX listing (wildcard) | **Blocked** (connection reset) | 0 | — |
| 2 | web.archive.org | CDX listing (exact URL) | **Blocked** (same) | 0 | — |

WHO host cap of 3 attempts reached; third Wayback attempt deliberately not spent. One web search found
no public GitHub/versioned archive of the provisional CSV.

## Results actually computed (vintage `who_prov_2026-10-17`, public-by 2026-10-17)

Coverage and maturity (`results/tables/coverage_by_year_who_prov_2026-10-17.csv`):

| Year t | Country rows | Complete H1 | Strict pairs (t vs t-1) | Relaxed pairs | H1 maturity (days) |
|---|---|---|---|---|---|
| 2020 | 104 | 104 | – | – | 2300 |
| 2021 | 128 | 117 | 42 | 60 | 1935 |
| 2022 | 117 | 108 | 53 | 75 | 1570 |
| 2023 | 99 | 83 | 43 | 55 | 1205 |
| 2024 | 101 | 80 | 30 | 46 | 839 |
| 2025 | 91 | 67 | 32 | 44 | 474 |
| 2026 | 7 | **0** | 0 | 0 | 109 |

* 200 strict pairs from 76 countries (max 5 pairs per country); 280 relaxed pairs; balanced
  2021–2025 strict panel = **10 countries** (50 pairs).
* Main exclusion reasons over 2021–2025: coverage-code change 85, incomplete H1 77, relaxed-only
  (some-units coverage, zero cell or base < 50) 80, frequency change 21.
* 2026: only January reported, by 7 countries, 109 days after H1 end — **no country has a complete
  H1 2026 in this vintage.** No negative cells; 233 zero cells concentrated in small-count countries.
* Within-vintage share of strict pairs with H1 decline >= 10%: **31/200 = 15.5%** (country-cluster
  bootstrap 95% CI 11.2–20.2%); balanced panel 10/50 = 20.0% (12.0–28.0%, 10 countries,
  descriptive only). Counts at 5/10/15/20%: 51/31/19/6 (strict), 80/53/36/20 (relaxed).
  These describe year-on-year change in one file, **not** revision reliability.

## Prior exploratory claims

| Claim | Status |
|---|---|
| 5/108 reversals at 10% across 64 countries; 103 stable | **NOT REPRODUCED** — requires earlier vintages; blocked |
| 0.03 buffer avoids all 5 while deferring 17 | **NOT REPRODUCED**; buffer fixed as predeclared primary rule, not re-tuned |
| Archive commits 105–135 days after H1 end | Not verifiable here. Consistent concern: at 109 days, the current file has no complete H1 2026 |

## Commands and tests

See `docs/REPRODUCIBILITY.md`. `pytest -q`: 12 passed (11 pipeline/unit + 1 dashboard AppTest).

## Next decision

Obtain >= 1 lawful earlier vintage (investigator-supplied archived files with capture evidence, or
re-run with `web.archive.org` allowed) or wait for the next WHO release to run the prospective test
in `docs/SCIENTIFIC_PROTOCOL.md`. Without that, move to RESERVE.
