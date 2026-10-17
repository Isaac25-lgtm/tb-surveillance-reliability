"""R02 results explorer. Reads only committed aggregate outputs in results/ (no raw files, no network,
no model fitting). Run: streamlit run dashboard/app.py

Default scope shows results derived from the current WHO public CSV only. Results derived from WHO
GTB-TME GitHub internal snapshots appear only with R02_SHOW_ARCHIVE_DERIVED=1 (see dashboard/safety.py
and docs/DEPLOYMENT.md).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from safety import REF, allowed_downloads, show_archive_derived  # noqa: E402
from tbvintage.evaluate import classify  # noqa: E402  same alert rule as the pipeline

TABLES, FIGS = ROOT / "results" / "tables", ROOT / "results" / "figures"
BLUE, ORANGE, MUTED = "#2f6db5", "#c4621d", "#59636e"  # validated pair (light and dark surfaces)
THRESHOLDS = (5, 10, 15, 20)
REFERENCE_LABEL = {"C1": "2026-10-17 public file", "S1": "2026-10-17 public file",
                   "S3": "next year's report snapshot"}
GIT_DATE_NOTE = ("git committer date: asserted by the committer's client, not a proven publication time")
FULL = show_archive_derived()

st.set_page_config(page_title="R02 TB vintage reliability", layout="wide")


@st.cache_data
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / name)


def figure(name: str, caption: str) -> None:
    p = FIGS / name
    if p.exists():
        st.image(str(p), caption=caption, width="stretch")


summary = json.loads((ROOT / "results" / "run_summary.json").read_text())
m = re.search(r"Overall\W+\*\*([A-Z_]+)\*\*", (ROOT / "docs" / "STATUS.md").read_text())
decision = m.group(1) if m else "see docs/STATUS.md"

st.info(
    f"**Decision: {decision}** · Retrospective, exploratory analysis of WHO *provisional TB notifications* "
    "(not incidence; no causal claims; no forecasting or ML) · Outputs from code commit "
    f"`{summary['code_commit'][:7]}` · Analysis created by the investigator, not by WHO; no WHO endorsement implied."
)
if not FULL:
    st.warning(
        "Showing results from the **current WHO public CSV only**. Cross-release reversal results use WHO "
        "GTB-TME GitHub internal snapshots whose reuse terms are unconfirmed, so they are withheld from this "
        "deployment (HOLD_DEPLOYMENT; see docs/DEPLOYMENT.md)."
    )

PAGES = ["Overview", "Sources and vintages", "Coverage and exclusions", "Within current file"]
if FULL:
    PAGES += ["Alert reversals", "Revision distributions", "Maturity", "Defer rule"]
PAGES += ["Downloads", "Limitations and licensing"]
page = st.sidebar.radio("Page", PAGES)
st.sidebar.caption("Values are read from committed result tables; nothing is simulated.")


def primary() -> tuple[pd.Series, pd.DataFrame]:
    a = table("cross_vintage_by_analysis.csv")
    row = a[(a.analysis == "C1") & (a.tier == "strict") & (a.metadata_rule == "identical")
            & (a["sample"] == "unbalanced")].iloc[0]
    b = table("cross_vintage_bootstrap.csv")
    return row, b


# --------------------------------------------------------------------------------------------- pages
if page == "Overview":
    st.title("Are TB notification decline alerts stable across WHO data vintages?")
    st.markdown(
        "WHO publishes **provisional** monthly/quarterly TB notifications and revises them. If a programme "
        "reads \"first-half (H1) notifications fell by at least 10%\" from one release, how often would a "
        "later release reverse that reading, and would a simple predeclared *verify-before-acting* rule pay off?"
    )
    if FULL:
        row, b = primary()
        g = table("defer_rule_grid.csv")
        pr = g[g.primary_rule & (g.analysis == "C1")].iloc[0]  # count columns do not vary by cost ratio
        ci = b[(b.analysis == "C1") & (b.tier == "strict") & (b.metadata_rule == "identical")
               & (b["sample"] == "unbalanced") & (b.statistic == "share_alert_changed_10")].iloc[0]
        c = st.columns(4)
        c[0].metric("Comparable country-years (C1)", int(row.n_units), help="Independent countries below")
        c[1].metric("Independent countries", int(row.n_countries))
        c[2].metric("Alerts changed at -10%", f"{int(row.changed_10)} / {int(row.n_units)}")
        c[3].metric("Stable at -10%", int(row.n_units - row.changed_10))
        st.markdown(
            f"**{ci.estimate:.1%}** of 10% alerts changed (country-cluster 95% CI {ci.ci_low:.1%}–{ci.ci_high:.1%}); "
            f"all {int(row.false_early_alarm_10)} were false early alarms, {int(row.early_miss_10)} early misses. "
            f"The predeclared buffer of {pr.buffer:g} would have deferred {int(pr.n_deferred)} of "
            f"{int(pr.n_decisions)} decisions and avoided {int(pr.errors_avoided)} reversals — "
            "**retrospectively only**."
        )
        st.caption("Early = WHO report-season snapshot for year t; reference = 2026-10-17 public CSV, a later "
                   "provisional file, **not truth**. The archived snapshots overlap earlier exploratory work and "
                   "the 0.03 buffer was inherited from it: there is no independent prospective validation.")
        figure("c1_revision_scatter.png", "C1: early vs reference H1 ratios (strict, identical metadata)")
    cov = table(f"coverage_by_year_{REF}.csv")
    st.subheader("The current public file thins out in recent years")
    ch = alt.Chart(cov.melt("year", ["country_years", "h1_complete"], "series", "countries")).mark_line(
        point=alt.OverlayMarkDef(size=60), strokeWidth=2).encode(
        x=alt.X("year:O", title="Year"), y=alt.Y("countries:Q", title="Countries"),
        color=alt.Color("series:N", scale=alt.Scale(range=[MUTED, BLUE]),
                        legend=alt.Legend(title=None, labelExpr="datum.label == 'h1_complete' ? "
                                          "'Complete H1' : 'Any provisional row'")),
        tooltip=["year", "series", "countries"])
    st.altair_chart(ch, width="stretch")
    st.caption("No country had a complete H1 2026 in the 2026-10-17 file (109 days after H1 ended).")

elif page == "Sources and vintages":
    st.title("Sources and vintages")
    st.markdown(
        "A vintage is one file identified by SHA-256. **Nominal snapshot date** is the date in WHO's file name "
        "(an internal extraction date). **Public-by** is the git *committer* date of the first commit containing "
        "the file: it is asserted by the committer's client, not a GitHub server timestamp, and is **not a "
        "proven publication time**. For the current CSV, public-by is our own access time."
    )
    inv = table("vintage_inventory.csv")
    if not FULL:
        inv = inv[inv.vintage_id == REF]
    cols = ["vintage_id", "source", "nominal_date", "public_by", "h1_latest_maturity_days_nominal",
            "h1_latest_maturity_days_public_by", "rows", "countries", "latest_year", "complete_h1_latest_year",
            "sha256"]
    st.dataframe(inv[cols], hide_index=True, width="stretch")
    if FULL:
        d = inv.assign(nominal=pd.to_datetime(inv.nominal_date, errors="coerce"),
                       public=pd.to_datetime(inv.public_by)).dropna(subset=["nominal"])
        lag = alt.Chart(d).mark_rule(strokeWidth=2, color=MUTED).encode(
            y=alt.Y("vintage_id:N", sort=alt.SortField("nominal"), title=None),
            x=alt.X("nominal:T", title="Date"), x2="public:T")
        pts = alt.Chart(d.melt(["vintage_id", "nominal"], ["nominal_date", "public_by"], "kind", "date")
                        .assign(date=lambda x: pd.to_datetime(x.date))).mark_point(size=70, filled=True).encode(
            y=alt.Y("vintage_id:N", sort=alt.SortField("nominal")), x="date:T",
            color=alt.Color("kind:N", scale=alt.Scale(range=[BLUE, ORANGE]), title="Date type"),
            shape="kind:N", tooltip=["vintage_id", "kind", "date:T"])
        st.altair_chart(lag + pts, width="stretch")
        st.caption("Gap between WHO's nominal snapshot date and the git committer date (public-by).")
    st.subheader("Every acquisition attempt (including failures and blocked hosts)")
    st.dataframe(pd.read_csv(ROOT / "data" / "manifest" / "source_attempts.csv"), hide_index=True,
                 width="stretch")

elif page == "Coverage and exclusions":
    st.title("Coverage and exclusions")
    st.subheader("Current public file: year pairs by inclusion status")
    flow = table(f"pair_flow_{REF}.csv")
    st.dataframe(flow, hide_index=True, width="stretch")
    st.dataframe(table(f"coverage_by_year_{REF}.csv"), hide_index=True, width="stretch")
    if FULL:
        st.subheader("Cross-vintage joins: compatible country-years and why others were excluded")
        ex = table("cross_vintage_exclusions.csv")
        c1, c2 = st.columns(2)
        an = c1.selectbox("Analysis", sorted(ex.analysis.unique()), index=sorted(ex.analysis.unique()).index("C1"))
        tier = c2.selectbox("Tier", ["strict", "relaxed"])
        sub = ex[(ex.analysis == an) & (ex.tier == tier)]
        st.dataframe(sub.pivot_table(index="status", columns="comparison", values="n_units", aggfunc="sum",
                                     fill_value=0), width="stretch")
        st.caption("`included` = same-definition in both files with identical frequency/coverage metadata. "
                   "`not_*_in_early:incomplete_h1` are country-years not yet complete when the early snapshot "
                   "was taken (no early decision existed).")
        inv = table("vintage_inventory.csv")
        st.subheader("Complete H1 for the newest year in each vintage")
        st.altair_chart(alt.Chart(inv).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
            x=alt.X("complete_h1_latest_year:Q", title="Countries with complete H1 (latest year in file)"),
            y=alt.Y("vintage_id:N", sort=alt.SortField("nominal_date"), title=None),
            tooltip=["vintage_id", "latest_year", "rows_latest_year", "complete_h1_latest_year",
                     "placeholder_rows_dropped"]), width="stretch")

elif page == "Within current file":
    st.title("Within the current public file (year-on-year change, not revision)")
    thr = table(f"threshold_counts_{REF}.csv")
    tier = st.radio("Sample", ["strict", "relaxed", "balanced"], horizontal=True)
    st.dataframe(thr[thr.tier == tier], hide_index=True, width="stretch")
    st.dataframe(table(f"within_vintage_bootstrap_{REF}.csv"), hide_index=True, width="stretch")
    figure(f"h1_ratios_{REF}.png", "Strict same-definition H1 ratios within the 2026-10-17 file")

elif page == "Alert reversals":
    st.title("Alert reversals between an early vintage and the reference")
    a = table("cross_vintage_by_analysis.csv")
    a = a[a.analysis != "S4"]
    f = st.columns(5)
    an = f[0].selectbox("Analysis", ["C1", "S1", "S3"], help="C1 primary; S1 2022 group; S3 next-report reference")
    tier = f[1].selectbox("Tier", ["strict", "relaxed"])
    meta = f[2].selectbox("Metadata rule", ["identical", "h1_equivalent"])
    sample = f[3].selectbox("Sample", ["unbalanced", "balanced"])
    k = f[4].selectbox("Decline threshold (%)", THRESHOLDS, index=1)
    row = a[(a.analysis == an) & (a.tier == tier) & (a.metadata_rule == meta) & (a["sample"] == sample)].iloc[0]
    c = st.columns(5)
    c[0].metric("Country-years", int(row.n_units))
    c[1].metric("Independent countries", int(row.n_countries))
    c[2].metric(f"Changed at -{k}%", int(row[f"changed_{k}"]))
    c[3].metric("Stable", int(row.n_units - row[f"changed_{k}"]))
    c[4].metric("False alarms / misses", f"{int(row[f'false_early_alarm_{k}'])} / {int(row[f'early_miss_{k}'])}")
    st.caption(f"Up to {int(row.max_units_per_country)} country-years per country; uncertainty below resamples "
               "whole countries.")

    b = table("cross_vintage_bootstrap.csv")
    bb = b[(b.analysis == an) & (b["sample"] == sample) & b.statistic.str.startswith("share_alert_changed")].copy()
    bb["threshold"] = bb.statistic.str.extract(r"(\d+)$").astype(int)
    bb["variant"] = bb.tier + " / " + bb.metadata_rule
    base = alt.Chart(bb).encode(x=alt.X("threshold:O", title="Decline threshold (%)"),
                                xOffset="variant:N", color=alt.Color("variant:N", title="Tier / metadata",
                                                                     scale=alt.Scale(range=[MUTED, BLUE, ORANGE])))
    st.altair_chart(base.mark_rule(strokeWidth=2).encode(y=alt.Y("ci_low:Q", title="Share of alerts changed",
                                                                 axis=alt.Axis(format="%")), y2="ci_high:Q")
                    + base.mark_point(size=70, filled=True).encode(
                        y="estimate:Q", tooltip=["variant", "threshold", "n_units", "n_countries",
                                                 alt.Tooltip("estimate:Q", format=".1%"),
                                                 alt.Tooltip("ci_low:Q", format=".1%"),
                                                 alt.Tooltip("ci_high:Q", format=".1%")]),
                    width="stretch")
    st.caption("Point = estimate; bar = country-cluster bootstrap 95% CI (2,000 resamples).")
    with st.expander("CI table"):
        st.dataframe(bb.drop(columns=["variant"]), hide_index=True, width="stretch")

    st.subheader("Country-years: early vs reference ratio")
    u = table("cross_vintage_units.csv")
    u = u[(u.analysis == an) & (u.tier == tier) & (u.metadata_rule == meta)].copy()
    if sample == "balanced":  # pipeline rule: country present in every comparison group of this analysis
        per_country = u.groupby("iso3")["comparison"].nunique()
        u = u[u.iso3.isin(per_country[per_country == u.comparison.nunique()].index)]
    late = table("cross_vintage_comparisons.csv").drop_duplicates("comparison").set_index("comparison")["late"]
    u["reference_file"] = u.comparison.map(late)
    st.caption(f"Chart sample ({sample}): {len(u)} country-years from {u.iso3.nunique()} countries, "
               "before the year/country filters below.")
    years = st.multiselect("Year t", sorted(u.year.unique()), default=sorted(u.year.unique()))
    country = st.selectbox("Country (ISO3)", ["All"] + sorted(u.iso3.unique()))
    u = u[u.year.isin(years)]
    if country != "All":
        u = u[u.iso3 == country]
    ea, eb = classify(u.ratio_a, k / 100).astype(bool), classify(u.ratio_b, k / 100).astype(bool)
    u["status"] = (ea != eb).map({True: "changed", False: "stable"})
    u["early_alert"], u["reference_alert"] = ea, eb
    cut = 1 - k / 100
    pts = alt.Chart(u).mark_point(filled=True, size=60, stroke="white", strokeWidth=1).encode(
        x=alt.X("ratio_a:Q", title="H1 ratio, early vintage", scale=alt.Scale(zero=False)),
        y=alt.Y("ratio_b:Q", title=f"H1 ratio, reference ({REFERENCE_LABEL[an]})", scale=alt.Scale(zero=False)),
        color=alt.Color("status:N", scale=alt.Scale(domain=["stable", "changed"], range=[BLUE, ORANGE])),
        shape=alt.Shape("status:N", scale=alt.Scale(domain=["stable", "changed"], range=["circle", "diamond"])),
        tooltip=["iso3", "year", "comparison", "reference_file",
                 alt.Tooltip("ratio_a:Q", format=".3f", title="early ratio"),
                 alt.Tooltip("ratio_b:Q", format=".3f", title="reference ratio"), alt.Tooltip("ratio_revision:Q", format="+.3f"),
                 "status"])
    rules = alt.Chart(pd.DataFrame({"v": [cut]})).mark_rule(color=ORANGE, strokeDash=[4, 4])
    st.altair_chart(pts + rules.encode(x="v:Q") + rules.encode(y="v:Q"), width="stretch")
    st.caption(f"{len(u)} country-years shown; dashed lines = -{k}% alert cut-off. Ratios are national "
               "aggregate notification totals, not individual patient data.")
    c1, c2 = st.columns(2)
    show = ["iso3", "year", "reference_file", "ratio_a", "ratio_b", "ratio_revision", "early_alert",
            "reference_alert"]
    c1.markdown(f"**Changed ({int((u.status == 'changed').sum())})**")
    c1.dataframe(u[u.status == "changed"][show], hide_index=True, width="stretch")
    c2.markdown(f"**Stable ({int((u.status == 'stable').sum())})**")
    c2.dataframe(u[u.status == "stable"][show], hide_index=True, width="stretch")

elif page == "Revision distributions":
    st.title("How much do H1 ratios and totals move?")
    u = table("cross_vintage_units.csv")
    f = st.columns(3)
    an = f[0].selectbox("Analysis", ["C1", "S1", "S3"])
    tier = f[1].selectbox("Tier", ["strict", "relaxed"])
    meta = f[2].selectbox("Metadata rule", ["identical", "h1_equivalent"])
    u = u[(u.analysis == an) & (u.tier == tier) & (u.metadata_rule == meta)]
    for col, title in (("ratio_revision", "Ratio revision (reference - early)"),
                       ("h1_revision_rel", "Relative revision of H1(t) total")):
        st.altair_chart(alt.Chart(u).mark_bar(color=BLUE, cornerRadiusEnd=2).encode(
            x=alt.X(f"{col}:Q", bin=alt.Bin(maxbins=40), title=title),
            y=alt.Y("count():Q", title="Country-years"), tooltip=["count():Q"]), width="stretch")
    st.dataframe(u[["ratio_revision", "h1_revision_rel"]].describe().T, width="stretch")
    st.caption("Many H1 totals are unchanged; a ratio can move because the comparison year (t-1) was revised.")

elif page == "Maturity":
    st.title("Maturity: when do early files become usable?")
    s4 = table("cross_vintage_comparisons.csv")
    s4 = s4[(s4.analysis == "S4") & (s4.tier == "strict") & (s4.metadata_rule == "identical")]
    st.dataframe(s4[["comparison", "n_units", "n_countries", "changed_10", "ratio_revision_abs_median"]],
                 hide_index=True, width="stretch")
    figure("s4_h1_2021_maturity.png", "H1 2021 country-years comparable to the reference, by 2021 snapshot")
    st.caption("All nine 2021 snapshots first appear in a commit with " + GIT_DATE_NOTE + " 2021-10-13, "
               "105 days after H1 ended; the report-season snapshots for 2023/2024/2025 have git committer "
               "dates 130/121/135 days after H1. The figure's axis label (\"made public by commit\") refers to "
               "this same git committer date.")

elif page == "Defer rule":
    st.title("Predeclared defer / verify rule")
    st.markdown("Defer (verify or wait) when the early ratio is within the buffer of the cut-off; otherwise act "
                "on the early vintage. Buffer 0.03 at -10% was **fixed in advance but inherited from earlier "
                "exploration of overlapping data** — this is a retrospective check, not validation.")
    g = table("defer_rule_grid.csv")
    g = g[(g.analysis == "C1") & (g.tier == "strict") & (g.metadata_rule == "identical")]
    f = st.columns(2)
    k = f[0].selectbox("Threshold (%)", THRESHOLDS, index=1)
    cr = f[1].select_slider("Cost of one deferral / cost of one wrong alert", sorted(g.cost_ratio.unique()),
                            value=0.2)
    gk = g[(g.threshold.round(2) == k / 100) & (g.cost_ratio == cr)].sort_values("buffer")
    st.dataframe(gk[["buffer", "n_decisions", "n_deferred", "errors_if_trust_early", "errors_after_defer_rule",
                     "errors_avoided", "loss_trust_early", "loss_defer_rule", "break_even_defer_to_error_cost",
                     "primary_rule"]], hide_index=True, width="stretch")
    long = gk.melt("buffer", ["n_deferred", "errors_after_defer_rule"], "series", "count")
    st.altair_chart(alt.Chart(long).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("buffer:Q", title="Buffer"), y=alt.Y("count:Q", title="Country-years"),
        color=alt.Color("series:N", scale=alt.Scale(range=[ORANGE, BLUE]), title=None),
        tooltip=["buffer", "series", "count"]), width="stretch")
    ga = g[g.threshold.round(2) == k / 100].melt(["buffer", "cost_ratio"], ["loss_trust_early", "loss_defer_rule"],
                                                 "policy", "loss")
    st.altair_chart(alt.Chart(ga).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("cost_ratio:Q", title="Deferral cost relative to one wrong alert"),
        y=alt.Y("loss:Q", title="Total loss (units of one wrong alert)"),
        color=alt.Color("policy:N", scale=alt.Scale(range=[BLUE, MUTED]), title=None),
        facet=alt.Facet("buffer:O", columns=4, title="Buffer"),
        tooltip=["buffer", "cost_ratio", "policy", "loss"]))
    st.caption("Costs are not measured; the break-even column is the deferral/error cost ratio below which "
               "deferring would have paid off in these retrospective data.")

elif page == "Downloads":
    st.title("Downloads (aggregate results only)")
    st.markdown("Allowlisted aggregate tables and figures. Raw WHO files, internal snapshot extracts, free-text "
                "fields and unit-level cross-vintage tables are not offered. Cite WHO and the reporting countries "
                "as the data source; the analysis is the investigator's.")
    for name, (path, desc) in allowed_downloads(FULL).items():
        mime = "text/csv" if name.endswith(".csv") else "image/png"
        st.download_button(f"{name} — {desc}", path.read_bytes(), file_name=name, mime=mime, key=name)

elif page == "Limitations and licensing":
    st.title("Limitations and licensing")
    st.markdown((ROOT / "docs" / "LIMITATIONS.md").read_text())
    st.markdown(
        "**Data sources and attribution.** Data: World Health Organization, Global Tuberculosis Programme — "
        "provisional TB notifications (accessed 2026-10-17) and, in full scope, WHO GTB-TME Global TB Report "
        "repositories; underlying data reported by countries and territories to WHO. This analysis was "
        "created by the investigator; it is not a WHO product and WHO does not endorse it. See "
        "docs/DEPLOYMENT.md for the licence audit."
    )
