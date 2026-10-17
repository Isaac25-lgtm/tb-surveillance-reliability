"""SYNTHETIC fixtures only. These numbers are invented for unit tests and are not WHO data."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tbvintage.preprocess import MONTHS, QUARTERS  # noqa: E402

COLS = ["country", "iso2", "iso3", "iso_numeric", "g_whoregion", "year",
        "report_frequency", "report_coverage", *MONTHS, *QUARTERS]


def row(iso3, year, freq=70, cov=34, h1=None, q=None):
    """Monthly row with H1 months ``h1`` (list of 6) or quarterly row with ``q`` (q1, q2)."""
    r = {c: None for c in COLS}
    r.update(country=f"Synthetic {iso3}", iso2=iso3[:2], iso3=iso3, iso_numeric="999",
             g_whoregion="AFR", year=year, report_frequency=freq, report_coverage=cov)
    if freq == 70:
        for m, v in zip(MONTHS, h1 or []):
            r[m] = v
    else:
        for qq, v in zip(QUARTERS, q or []):
            r[qq] = v
    return r


def monthly(total):
    """Six equal months summing to ``total`` (total divisible by 6 not required)."""
    base = [total // 6] * 6
    base[0] += total - sum(base)
    return base


@pytest.fixture
def synthetic_frame():
    rows = [
        # AAA: clean monthly, all units, 600 -> 540 (ratio 0.90, exactly at the 10% threshold)
        row("AAA", 2021, h1=monthly(600)), row("AAA", 2022, h1=monthly(540)),
        # BBB: switches monthly -> quarterly: frequency_change
        row("BBB", 2021, h1=monthly(300)), row("BBB", 2022, freq=71, q=[100, 100]),
        # CCC: some-units coverage both years: relaxed only
        row("CCC", 2021, cov=35, h1=monthly(300)), row("CCC", 2022, cov=35, h1=monthly(330)),
        # DDD: missing May in 2022: incomplete
        row("DDD", 2021, h1=monthly(300)), row("DDD", 2022, h1=[50, 50, 50, 50, None, 50]),
        # EEE: tiny counts with a zero month: relaxed only (zero cell, base < 50)
        row("EEE", 2021, h1=[1, 0, 2, 1, 1, 1]), row("EEE", 2022, h1=[1, 1, 1, 1, 1, 1]),
        # FFF: quarterly clean 400 -> 300 (ratio 0.75)
        row("FFF", 2021, freq=71, q=[200, 200]), row("FFF", 2022, freq=71, q=[150, 150]),
    ]
    return pd.DataFrame(rows, columns=COLS)


def write_vintage(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
