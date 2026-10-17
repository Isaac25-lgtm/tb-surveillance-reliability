"""R02 vintage explorer: reads only the small aggregate CSVs in results/tables (no raw files, no network).

Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"

st.set_page_config(page_title="R02 TB vintage explorer", layout="wide")

summary = json.loads((ROOT / "results" / "run_summary.json").read_text())
vintages = [v["id"] for v in summary["vintages"]]
status = pd.read_csv(TABLES / "cross_vintage_status.csv")
n_cmp = int((status["status"] == "COMPUTED").sum())

st.title("Are TB notification decline alerts stable across WHO data vintages?")
st.info(
    f"**Stage:** checkpoint 1 · **Decision:** HOLD_ACCESS · **Verified vintages:** {len(vintages)} "
    f"({', '.join(vintages)}) · **Cross-vintage comparisons computed:** {n_cmp} · "
    f"**Run code commit:** `{summary['code_commit'][:7]}` · All figures are observed WHO provisional "
    "notifications (not incidence); nothing here is simulated or a forecast."
)

tab_over, tab_prov, tab_pairs, tab_rev, tab_lim = st.tabs(
    ["Overview", "Data provenance", "Within-vintage pairs", "Cross-vintage revisions", "Limitations"])

with tab_over:
    st.markdown(
        "This explorer shows how many countries have **same-definition first-half (H1)** provisional "
        "notification totals, and how often year-on-year H1 changes cross decline thresholds. "
        "Revision reliability *between* releases requires at least two verified vintages."
    )
    vid = st.selectbox("Vintage", vintages)
    cov = pd.read_csv(TABLES / f"coverage_by_year_{vid}.csv")
    st.image(str(FIGS / f"coverage_{vid}.png"), use_container_width=True)
    st.dataframe(cov, hide_index=True, use_container_width=True)

with tab_prov:
    st.markdown("Every acquisition attempt, including failures and blocked hosts, as recorded in "
                "`data/manifest/source_attempts.csv`.")
    st.dataframe(pd.read_csv(ROOT / "data" / "manifest" / "source_attempts.csv"), hide_index=True,
                 use_container_width=True)

with tab_pairs:
    vid = st.selectbox("Vintage ", vintages)
    thr = pd.read_csv(TABLES / f"threshold_counts_{vid}.csv")
    tier = st.radio("Sample", sorted(thr["tier"].unique()), horizontal=True)
    st.dataframe(thr[thr["tier"] == tier], hide_index=True, use_container_width=True)
    st.image(str(FIGS / f"h1_ratios_{vid}.png"), use_container_width=True)
    ratios = pd.read_csv(TABLES / f"h1_ratios_strict_{vid}.csv")
    country = st.selectbox("Country (strict pairs only)", ["All"] + sorted(ratios["country"].unique()))
    view = ratios if country == "All" else ratios[ratios["country"] == country]
    st.dataframe(view, hide_index=True, use_container_width=True)
    st.caption("Within-vintage year-on-year change. Countries absent here had no strict same-definition "
               "pair; that is missing data, not 'no decline'.")

with tab_rev:
    st.dataframe(status, hide_index=True, use_container_width=True)
    if n_cmp == 0:
        st.warning("Not computable: only one verified vintage. The earlier exploratory result "
                   "(5/108 reversals at the 10% threshold) is **not reproduced** here.")

with tab_lim:
    st.markdown((ROOT / "docs" / "LIMITATIONS.md").read_text())
