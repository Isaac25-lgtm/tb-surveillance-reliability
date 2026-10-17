"""Immutable raw WHO provisional file -> first-half (H1) country-year totals with provenance flags.

H1 rule (predeclared in docs/SCIENTIFIC_PROTOCOL.md):
  * report_frequency 70 (monthly): H1 = m_01..m_06, all six present.
  * report_frequency 71 (quarterly): H1 = q_1 + q_2, both present.
Rows whose cells are missing are kept and flagged, never silently dropped.
"""

from __future__ import annotations

import pandas as pd

MONTHS = [f"m_{i:02d}" for i in range(1, 13)]
QUARTERS = [f"q_{i}" for i in range(1, 5)]
H1_MONTHS = MONTHS[:6]
H1_QUARTERS = QUARTERS[:2]
MONTHLY, QUARTERLY = 70, 71
ALL_UNITS, SOME_UNITS = 34, 35

REQUIRED_COLUMNS = [
    "country", "iso3", "g_whoregion", "year", "report_frequency", "report_coverage",
    *MONTHS, *QUARTERS,
]


# Columns never loaded from WHO internal snapshots: free-text remarks can name individuals,
# and gaps.na is undocumented.
DROP_COLUMNS = ("remarks", "gaps_na")


def read_snapshot(path: str) -> tuple[pd.DataFrame, int]:
    """Read a public CSV or a WHO GTB-TME internal snapshot (.rda or dotted-name CSV).

    Harmonises ``report.frequency``/``m.01`` names to the public ``_`` schema, drops free-text
    and undocumented columns, and drops placeholder rows whose 16 count cells are all missing.
    Returns the frame and the number of placeholder rows dropped.
    """
    if str(path).endswith(".rda"):
        import rdata  # optional dependency, only needed for archived snapshots

        objs = rdata.read_rda(str(path))
        if len(objs) != 1:
            raise ValueError(f"{path}: expected one R object, found {list(objs)}")
        df = pd.DataFrame(next(iter(objs.values())))
    else:
        try:
            df = pd.read_csv(path, dtype={"iso_numeric": str, "iso2": str})
        except UnicodeDecodeError:
            df = pd.read_csv(path, dtype={"iso_numeric": str, "iso2": str}, encoding="latin-1")
    df = df.rename(columns=lambda c: c.replace(".", "_"))
    df = df.drop(columns=[c for c in DROP_COLUMNS if c in df.columns])
    if "g_whoregion" not in df.columns:
        df["g_whoregion"] = pd.NA
    cells = [c for c in MONTHS + QUARTERS if c in df.columns]
    for c in cells + ["year", "report_frequency", "report_coverage"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    placeholder = df[cells].isna().all(axis=1)
    df = df.loc[~placeholder].copy()
    df["year"] = df["year"].astype(int)
    return df.reset_index(drop=True), int(placeholder.sum())


def load_vintage(path: str, vintage_id: str) -> pd.DataFrame:
    df, n_placeholder = read_snapshot(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"vintage {vintage_id}: missing columns {missing}")
    if df.duplicated(["iso3", "year"]).any():
        raise ValueError(f"vintage {vintage_id}: duplicate iso3-year keys")
    df = df.copy()
    df["vintage_id"] = vintage_id
    df.attrs["placeholder_rows_dropped"] = n_placeholder
    return df


def h1_totals(df: pd.DataFrame) -> pd.DataFrame:
    """One row per country-year with H1 total and completeness/zero flags."""
    freq = df["report_frequency"]
    is_m = freq.eq(MONTHLY)
    is_q = freq.eq(QUARTERLY)
    cells_m = df[H1_MONTHS]
    cells_q = df[H1_QUARTERS]
    n_missing = (cells_m.isna().sum(axis=1)).where(is_m, cells_q.isna().sum(axis=1))
    n_missing = n_missing.where(is_m | is_q, pd.NA)
    has_zero = (cells_m.eq(0).any(axis=1)).where(is_m, cells_q.eq(0).any(axis=1))
    total = cells_m.sum(axis=1, min_count=6).where(is_m, cells_q.sum(axis=1, min_count=2))
    out = df[["vintage_id", "iso3", "country", "g_whoregion", "year",
              "report_frequency", "report_coverage"]].copy()
    out["h1_missing_cells"] = n_missing
    out["h1_complete"] = (is_m | is_q) & n_missing.eq(0)
    out["h1_has_zero"] = has_zero & out["h1_complete"]
    out["h1_total"] = total.where(out["h1_complete"])
    return out.reset_index(drop=True)
