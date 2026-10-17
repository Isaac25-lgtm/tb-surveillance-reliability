"""Deployment scope and download allowlist for the R02 explorer.

Two scopes:
  * ``public_csv`` (DEFAULT): only results derived from the current WHO public provisional CSV.
  * ``full``: also results derived from WHO GTB-TME GitHub internal snapshots. Set the environment
    variable R02_SHOW_ARCHIVE_DERIVED=1. Reuse rights for those snapshots are unclear
    (docs/DEPLOYMENT.md), so a public deployment must keep the default until they are clarified.

Only files listed here can be offered for download. Raw inputs (.rda/.csv), free-text remarks,
unit-level cross-vintage extracts and per-country H1 totals are never offered.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = "who_prov_2026-10-17"

PUBLIC_TABLES = {
    f"coverage_by_year_{REF}.csv": "Coverage, completeness and maturity by year (current public file)",
    f"pair_flow_{REF}.csv": "Year-pair inclusion/exclusion flow (current public file)",
    f"threshold_counts_{REF}.csv": "Within-file decline counts at 5/10/15/20% (current public file)",
    f"within_vintage_bootstrap_{REF}.csv": "Country-cluster CI, within-file decline share",
}
ARCHIVE_TABLES = {
    "vintage_inventory.csv": "16 verified vintages: hashes, nominal vs git-commit dates, coverage",
    "cross_vintage_exclusions.csv": "Join/exclusion audit per comparison and tier",
    "cross_vintage_comparisons.csv": "Reversals and revision summaries per comparison",
    "cross_vintage_by_analysis.csv": "Aggregated reversals by analysis, tier, metadata rule, sample",
    "cross_vintage_bootstrap.csv": "Country-cluster bootstrap CIs on revision outcomes",
    "defer_rule_grid.csv": "Defer rule over thresholds x buffers x cost ratios",
}
PUBLIC_FIGURES = {
    f"coverage_{REF}.png": "Coverage by year (current public file)",
    f"h1_ratios_{REF}.png": "Within-file H1 ratios (current public file)",
}
ARCHIVE_FIGURES = {
    "c1_revision_scatter.png": "Early vs reference H1 ratios (C1)",
    "c1_defer_tradeoff.png": "Defer-rule trade-off (C1)",
    "s4_h1_2021_maturity.png": "H1 2021 maturity across 2021 snapshots (S4)",
}
# Never downloadable even in full scope: unit-level extracts and per-country H1 totals.
NEVER_DOWNLOAD = {"cross_vintage_units.csv", f"h1_ratios_strict_{REF}.csv"}


def show_archive_derived() -> bool:
    return os.environ.get("R02_SHOW_ARCHIVE_DERIVED", "") == "1"


def allowed_downloads(full: bool) -> dict[str, tuple[Path, str]]:
    """Map download file name -> (path, description) for the given scope."""
    tables = {**PUBLIC_TABLES, **(ARCHIVE_TABLES if full else {})}
    figs = {**PUBLIC_FIGURES, **(ARCHIVE_FIGURES if full else {})}
    out = {n: (ROOT / "results" / "tables" / n, d) for n, d in tables.items()}
    out.update({n: (ROOT / "results" / "figures" / n, d) for n, d in figs.items()})
    assert not NEVER_DOWNLOAD & set(out)
    return {n: v for n, v in out.items() if v[0].exists()}
