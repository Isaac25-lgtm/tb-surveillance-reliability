"""Schema, coverage and maturity audit of one vintage."""

from __future__ import annotations

from datetime import date

import pandas as pd

from .preprocess import ALL_UNITS, MONTHLY, MONTHS, QUARTERLY, QUARTERS, SOME_UNITS


def coverage_by_year(raw: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    cells = raw[MONTHS + QUARTERS]
    g = pd.DataFrame({
        "year": raw["year"],
        "monthly": raw["report_frequency"].eq(MONTHLY),
        "quarterly": raw["report_frequency"].eq(QUARTERLY),
        "cov_all_units": raw["report_coverage"].eq(ALL_UNITS),
        "cov_some_units": raw["report_coverage"].eq(SOME_UNITS),
        "cov_missing": raw["report_coverage"].isna(),
        "any_zero_cell": cells.eq(0).any(axis=1),
        "any_negative_cell": cells.lt(0).any(axis=1),
        "h1_complete": h1["h1_complete"].astype(bool).values,
        "h1_complete_with_zero": h1["h1_has_zero"].astype(bool).values,
    })
    out = g.groupby("year").sum().astype(int)
    out.insert(0, "country_years", raw.groupby("year").size())
    return out.reset_index()


def h1_maturity_days(year: int, vintage_date: date) -> int:
    """Days between end of H1 (30 June of ``year``) and the vintage date."""
    return (vintage_date - date(year, 6, 30)).days
