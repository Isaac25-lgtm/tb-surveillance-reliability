"""R02 vintage explorer: reads only the small aggregate CSVs in results/ (no raw files, no network).

Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"


def table(name: str) -> pd.DataFrame | None:
    p = TABLES / name
    return pd.read_csv(p) if p.exists() else None


def figure(name: str) -> None:
    p = FIGS / name
    if p.exists():
        st.image(str(p), use_container_width=True)


st.set_page_config(page_title="R02 TB vintage explorer", layout="wide")

summary = json.loads((ROOT / "results" / "run_summary.json").read_text())
m = re.search(r"Overall\W+\*\*([A-Z_]+)\*\*", (ROOT / "docs" / "STATUS.md").read_text())
decision = m.group(1) if m else "see docs/STATUS.md"
reference_ids = sorted(p.stem.removeprefix("coverage_by_year_") for p in TABLES.glob("coverage_by_year_*.csv"))
inventory = table("vintage_inventory.csv")
status = table("cross_vintage_status.csv")
computed = status is not None and (status["status"] == "COMPUTED").any()
n_vintages = len(inventory) if inventory is not None else len(summary.get("vintages", []))

st.title("Are TB notification decline alerts stable across WHO data vintages?")
st.info(
    f"**Decision:** {decision} · **Verified vintages:** {n_vintages} · "
    f"**Cross-vintage comparisons:** {'computed' if computed else 'not computable'} · "
    f"**Run code commit:** `{summary['code_commit'][:7]}` · Observed WHO provisional notifications "
    "(not incidence); nothing here is simulated or a forecast. Cross-vintage results are "
    "retrospective and exploratory."
)

tabs = st.tabs(["Overview", "Data provenance", "Within-vintage pairs", "Cross-vintage revisions", "Limitations"])

with tabs[0]:
    st.markdown("Coverage of **same-definition first-half (H1)** provisional notification totals in the "
                "reference (most recent public) file.")
    vid = st.selectbox("Reference vintage", reference_ids)
    figure(f"coverage_{vid}.png")
    st.dataframe(table(f"coverage_by_year_{vid}.csv"), hide_index=True, use_container_width=True)

with tabs[1]:
    st.markdown("Every acquisition attempt, including failures and blocked hosts "
                "(`data/manifest/source_attempts.csv`).")
    st.dataframe(pd.read_csv(ROOT / "data" / "manifest" / "source_attempts.csv"), hide_index=True,
                 use_container_width=True)
    if inventory is not None:
        st.markdown("Verified vintages. `public_by` is the earliest provable public existence (git commit "
                    "date or our access time), not the nominal snapshot date.")
        st.dataframe(inventory, hide_index=True, use_container_width=True)

with tabs[2]:
    vid = st.selectbox("Reference vintage ", reference_ids)
    thr = table(f"threshold_counts_{vid}.csv")
    tier = st.radio("Sample", sorted(thr["tier"].unique()), horizontal=True)
    st.dataframe(thr[thr["tier"] == tier], hide_index=True, use_container_width=True)
    figure(f"h1_ratios_{vid}.png")
    ratios = table(f"h1_ratios_strict_{vid}.csv")
    country = st.selectbox("Country (strict pairs only)", ["All"] + sorted(ratios["country"].unique()))
    st.dataframe(ratios if country == "All" else ratios[ratios["country"] == country], hide_index=True,
                 use_container_width=True)
    st.caption("Within-vintage year-on-year change. Countries absent here had no strict same-definition "
               "pair; that is missing data, not 'no decline'.")

with tabs[3]:
    st.dataframe(status, hide_index=True, use_container_width=True)
    if not computed:
        st.warning("Not computable: fewer than two verified vintages. The earlier exploratory result "
                   "(5/108 reversals at the 10% threshold) is **not reproduced** here.")
    else:
        st.markdown("Primary: analysis **C1**, strict tier, `identical` reporting metadata across releases. "
                    "The later file is a reference, not truth.")
        figure("c1_revision_scatter.png")
        for title, name in (("Results by analysis", "cross_vintage_by_analysis.csv"),
                            ("Country-cluster bootstrap on revision outcomes", "cross_vintage_bootstrap.csv"),
                            ("Join/exclusion audit", "cross_vintage_exclusions.csv")):
            df = table(name)
            if df is not None:
                st.subheader(title)
                st.dataframe(df, hide_index=True, use_container_width=True)
        defer = table("defer_rule_grid.csv")
        if defer is not None:
            st.subheader("Defer rule (0.03 buffer predeclared, retrospective)")
            figure("c1_defer_tradeoff.png")
            st.dataframe(defer[defer["primary_rule"]], hide_index=True, use_container_width=True)
        figure("s4_h1_2021_maturity.png")

with tabs[4]:
    st.markdown((ROOT / "docs" / "LIMITATIONS.md").read_text())
