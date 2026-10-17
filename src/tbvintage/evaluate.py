"""Paired H1 comparisons, threshold alerts, cross-vintage revision and defer-rule evaluation.

Terminology
  * year pair: H1 of year t versus H1 of year t-1 for one country within one vintage.
  * ratio r = H1_t / H1_{t-1}; a decline alert at threshold k fires when r <= 1 - k.
  * cross-vintage comparison: the same (country, t) year pair classified in an
    earlier vintage A and a later vintage B. B is the *later-file reference*, not
    true TB incidence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .preprocess import ALL_UNITS

THRESHOLDS = (0.05, 0.10, 0.15, 0.20)


def year_pairs(h1: pd.DataFrame, min_base: float = 50.0) -> pd.DataFrame:
    """Build consecutive-year pairs and label their comparability tier.

    tier 'strict': both H1 complete, same reporting frequency, both all-units
      coverage (34), no zero H1 cell, base H1 >= min_base.
    tier 'relaxed': both complete, same frequency, same coverage code (missing
      treated as its own code), base H1 > 0. Every strict pair is also relaxed.
    """
    cur = h1.copy()
    prev = h1.copy()
    prev["year"] = prev["year"] + 1
    keys = ["vintage_id", "iso3", "year"]
    cols = ["report_frequency", "report_coverage", "h1_complete", "h1_has_zero", "h1_total"]
    p = cur.merge(prev[keys + cols], on=keys, how="inner", suffixes=("", "_prev"))
    same_freq = p["report_frequency"].eq(p["report_frequency_prev"])
    cov = p["report_coverage"].fillna(-1)
    cov_prev = p["report_coverage_prev"].fillna(-1)
    complete = p["h1_complete"].astype(bool) & p["h1_complete_prev"].astype(bool)
    relaxed = complete & same_freq & cov.eq(cov_prev) & p["h1_total_prev"].gt(0)
    strict = (
        complete & same_freq & cov.eq(ALL_UNITS) & cov_prev.eq(ALL_UNITS)
        & ~p["h1_has_zero"].astype(bool) & ~p["h1_has_zero_prev"].astype(bool)
        & p["h1_total_prev"].ge(min_base)
    )
    p["relaxed"] = relaxed
    p["strict"] = strict
    p["exclusion_reason"] = np.select(
        [~complete, ~same_freq, ~cov.eq(cov_prev), ~p["h1_total_prev"].gt(0), strict],
        ["incomplete_h1", "frequency_change", "coverage_change", "zero_base", "included_strict"],
        default="relaxed_only",
    )
    p["ratio"] = (p["h1_total"] / p["h1_total_prev"]).where(relaxed)
    return p


EPS = 1e-9  # guards the inclusive boundary against float representation (e.g. 1 - 0.15)


def classify(ratio: pd.Series, k: float) -> pd.Series:
    """Decline alert (True) when ratio <= 1 - k; NaN where the ratio is undefined."""
    return ratio.le(1 - k + EPS).where(ratio.notna())


def balanced_countries(pairs: pd.DataFrame, years: list[int], tier: str = "strict") -> set[str]:
    """Countries with a pair of the given tier in every listed year t."""
    ok = pairs[pairs[tier] & pairs["year"].isin(years)]
    counts = ok.groupby("iso3")["year"].nunique()
    return set(counts[counts == len(set(years))].index)


def threshold_summary(pairs: pd.DataFrame, tier: str, thresholds=THRESHOLDS) -> pd.DataFrame:
    rows = []
    sub = pairs[pairs[tier]]
    for (vid, year), g in sub.groupby(["vintage_id", "year"]):
        row = {"vintage_id": vid, "year": int(year), "tier": tier, "n_pairs": len(g),
               "median_ratio": float(g["ratio"].median())}
        for k in thresholds:
            row[f"decline_ge_{int(round(k * 100))}pct"] = int(classify(g["ratio"], k).sum())
        rows.append(row)
    return pd.DataFrame(rows)


# Reporting definition of a year pair: frequency and coverage code in year t and year t-1.
METADATA = ["report_frequency", "report_frequency_prev", "report_coverage", "report_coverage_prev"]
METADATA_RULES = ("identical", "h1_equivalent")


def audit_cross_vintage(pairs_a: pd.DataFrame, pairs_b: pd.DataFrame, tier: str = "strict",
                        years=None) -> pd.DataFrame:
    """Every (iso3, year) unit in either vintage for the selected years, with a join status.

    Status values
      included                  tier-eligible in both, identical reporting metadata in both
      metadata_changed:<fields> tier-eligible in both, but frequency/coverage differ between vintages
      absent_in_late            eligible early, no pair row in the later vintage
      not_<tier>_in_late:<why>  eligible early, pair row exists later but fails the tier
      not_<tier>_in_early:<why> eligible later only (no early decision existed)
    Missing coverage codes compare equal to each other.
    """
    if years is not None:
        pairs_a = pairs_a[pairs_a["year"].isin(list(years))]
        pairs_b = pairs_b[pairs_b["year"].isin(list(years))]
    keep = ["iso3", "year", "ratio", "h1_total", "h1_total_prev", tier, "exclusion_reason", *METADATA]
    j = pairs_a[keep].merge(pairs_b[keep], on=["iso3", "year"], how="outer", suffixes=("_a", "_b"),
                            indicator=True)
    elig_a = j[f"{tier}_a"].fillna(False).astype(bool)
    elig_b = j[f"{tier}_b"].fillna(False).astype(bool)
    changed = []
    for m in METADATA:
        diff = j[f"{m}_a"].fillna(-1) != j[f"{m}_b"].fillna(-1)
        changed.append(diff.map({True: m, False: ""}))
    changed_fields = pd.concat(changed, axis=1).apply(lambda r: "+".join(x for x in r if x), axis=1)
    status = pd.Series("", index=j.index, dtype=object)
    both = elig_a & elig_b
    status[both & changed_fields.eq("")] = "included"
    status[both & changed_fields.ne("")] = "metadata_changed:" + changed_fields[both & changed_fields.ne("")]
    a_only = elig_a & ~elig_b
    status[a_only & j["_merge"].eq("left_only")] = "absent_in_late"
    late_fail = a_only & j["_merge"].eq("both")
    status[late_fail] = f"not_{tier}_in_late:" + j.loc[late_fail, "exclusion_reason_b"].astype(str)
    b_only = elig_b & ~elig_a
    status[b_only] = f"not_{tier}_in_early:" + j.loc[b_only, "exclusion_reason_a"].fillna("absent").astype(str)
    j["status"] = status
    j["metadata_changed_fields"] = changed_fields
    return j[status.ne("")].drop(columns=["_merge"]).reset_index(drop=True)


def compare_vintages(pairs_a: pd.DataFrame, pairs_b: pd.DataFrame, tier: str = "strict",
                     thresholds=THRESHOLDS, years=None, metadata: str = "identical") -> pd.DataFrame:
    """Join the same (iso3, year) pair across an earlier vintage A and later vintage B.

    The pair must meet ``tier`` in both vintages. With ``metadata="identical"`` (primary) the
    reporting frequency and coverage code of years t and t-1 must also be identical in both
    vintages. ``metadata="h1_equivalent"`` (labelled sensitivity) additionally admits units whose
    metadata differ between vintages, treating each vintage's H1 total as equivalent.
    ``years`` optionally restricts to year t values.
    """
    if metadata not in METADATA_RULES:
        raise ValueError(f"metadata must be one of {METADATA_RULES}")
    aud = audit_cross_vintage(pairs_a, pairs_b, tier, years)
    ok = aud["status"].eq("included")
    if metadata == "h1_equivalent":
        ok |= aud["status"].str.startswith("metadata_changed:")
    j = aud[ok].drop(columns=[f"{tier}_a", f"{tier}_b", "exclusion_reason_a", "exclusion_reason_b"])
    j = j.reset_index(drop=True)
    j["ratio_revision"] = j["ratio_b"] - j["ratio_a"]
    j["h1_revision_rel"] = j["h1_total_b"] / j["h1_total_a"] - 1
    for k in thresholds:
        tag = int(round(k * 100))
        ca = classify(j["ratio_a"], k).astype(bool)
        cb = classify(j["ratio_b"], k).astype(bool)
        j[f"changed_{tag}"] = ca != cb
        j[f"false_early_alarm_{tag}"] = ca & ~cb
        j[f"early_miss_{tag}"] = ~ca & cb
    return j


def defer_rule(cmp: pd.DataFrame, k: float, buffer: float, cost_defer: float = 1.0,
               cost_error: float = 1.0) -> dict:
    """Predeclared rule: defer/verify when |r_A - (1-k)| < buffer, else act on vintage A.

    Errors are judged against the later vintage B (a later file, not ground truth).
    """
    cut = 1 - k
    near = (cmp["ratio_a"] - cut).abs() < buffer
    ca = classify(cmp["ratio_a"], k).astype(bool)
    cb = classify(cmp["ratio_b"], k).astype(bool)
    wrong = ca != cb
    n = len(cmp)
    n_defer = int(near.sum())
    err_acted = int((wrong & ~near).sum())
    err_trust = int(wrong.sum())
    avoided = err_trust - err_acted
    return {
        "threshold": k, "buffer": buffer, "n_decisions": n, "n_deferred": n_defer,
        "errors_if_trust_early": err_trust, "errors_after_defer_rule": err_acted,
        "errors_avoided": avoided,
        "loss_trust_early": cost_error * err_trust,
        "loss_defer_rule": cost_error * err_acted + cost_defer * n_defer,
        # defer rule is worthwhile when cost_defer / cost_error < this value
        "break_even_defer_to_error_cost": (avoided / n_defer) if n_defer else float("nan"),
    }


def cluster_bootstrap(df: pd.DataFrame, stat, cluster: str = "iso3", n_boot: int = 2000,
                      seed: int = 20261017, alpha: float = 0.05) -> tuple[float, float, float]:
    """Percentile CI from resampling whole countries with replacement."""
    rng = np.random.default_rng(seed)
    df = df.reset_index(drop=True)
    groups = {c: g.index.to_numpy() for c, g in df.groupby(cluster)}  # row positions per country
    ids = np.array(list(groups))
    est = float(stat(df))
    if len(ids) < 2:
        return est, float("nan"), float("nan")
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(ids, size=len(ids), replace=True)
        rows = np.concatenate([groups[c] for c in pick])
        draws.append(stat(df.iloc[rows].reset_index(drop=True)))
    lo, hi = np.nanquantile(draws, [alpha / 2, 1 - alpha / 2])
    return est, float(lo), float(hi)
