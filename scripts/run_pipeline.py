"""Run the R02 pipeline on every hash-verified vintage in configs/experiment.yaml.

Usage: python scripts/run_pipeline.py [--config configs/experiment.yaml] [--out results]
Raw files are read from data/raw/ (git-ignored); only aggregate outputs are written.

Outputs
  * reference-vintage audit (coverage, pair flow, threshold counts, within-vintage bootstrap);
  * inventory of all vintages (rows, coverage, maturity at nominal and public-by dates);
  * every configured cross-vintage comparison, aggregated by analysis (C1 primary, S1/S3/S4);
  * defer-rule grid and country-cluster bootstrap for each analysis.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tbvintage import audit, evaluate, figures, preprocess  # noqa: E402
from tbvintage.acquire import sha256_file  # noqa: E402


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def pct(k: float) -> int:
    return int(round(k * 100))


def reference_outputs(v, raw, h1, pairs, cfg, out, ks) -> dict:
    """Single-vintage audit tables and figures (unchanged checkpoint-1 outputs)."""
    vid = v["id"]
    cov = audit.coverage_by_year(raw, h1)
    vdate = date.fromisoformat(v["public_by"])
    cov["h1_maturity_days_at_vintage"] = [audit.h1_maturity_days(int(y), vdate) for y in cov["year"]]
    cov.to_csv(out / f"tables/coverage_by_year_{vid}.csv", index=False)

    flow = pairs.groupby(["year", "exclusion_reason"]).size().unstack(fill_value=0)
    flow["strict"] = pairs.groupby("year")["strict"].sum()
    flow["relaxed"] = pairs.groupby("year")["relaxed"].sum()
    flow["pairs_with_both_years_present"] = pairs.groupby("year").size()
    flow = flow.reset_index()
    flow.to_csv(out / f"tables/pair_flow_{vid}.csv", index=False)

    bal = evaluate.balanced_countries(pairs, cfg["balanced_years"], "strict")
    pairs = pairs.assign(balanced=pairs["strict"] & pairs["iso3"].isin(bal))
    thr = pd.concat([evaluate.threshold_summary(pairs, t, ks) for t in ("strict", "relaxed", "balanced")])
    thr.to_csv(out / f"tables/threshold_counts_{vid}.csv", index=False)

    cols = ["iso3", "country", "g_whoregion", "year", "report_frequency", "h1_total_prev", "h1_total", "ratio"]
    pairs.loc[pairs["strict"], cols].sort_values(["year", "iso3"]).to_csv(
        out / f"tables/h1_ratios_strict_{vid}.csv", index=False)

    strict = pairs[pairs["strict"]]
    k0 = cfg["primary_threshold"]
    boot = []
    for name, df in (("all_strict_pairs", strict), ("balanced_strict_pairs", strict[strict["iso3"].isin(bal)])):
        if df.empty:
            continue
        est, lo, hi = evaluate.cluster_bootstrap(
            df, lambda d: evaluate.classify(d["ratio"], k0).mean(),
            n_boot=cfg["bootstrap"]["n_boot"], seed=cfg["seed"], alpha=cfg["bootstrap"]["alpha"])
        boot.append({"sample": name, "statistic": f"share of pairs with H1 decline >= {k0:.0%}",
                     "n_pairs": len(df), "n_countries": df["iso3"].nunique(),
                     "max_pairs_per_country": int(df.groupby("iso3").size().max()),
                     "estimate": est, "ci_low": lo, "ci_high": hi})
    pd.DataFrame(boot).to_csv(out / f"tables/within_vintage_bootstrap_{vid}.csv", index=False)
    figures.coverage_figure(cov, flow, vid, str(out / f"figures/coverage_{vid}.png"))
    figures.ratio_figure(pairs, vid, str(out / f"figures/h1_ratios_{vid}.png"), ks)
    return {"strict_countries": int(strict["iso3"].nunique()), "balanced_countries": len(bal)}


def summarise_comparison(cmp_: pd.DataFrame, ks) -> dict:
    row = {"n_units": len(cmp_), "n_countries": int(cmp_["iso3"].nunique())}
    if cmp_.empty:
        return row
    for k in ks:
        t = pct(k)
        row[f"changed_{t}"] = int(cmp_[f"changed_{t}"].sum())
        row[f"false_early_alarm_{t}"] = int(cmp_[f"false_early_alarm_{t}"].sum())
        row[f"early_miss_{t}"] = int(cmp_[f"early_miss_{t}"].sum())
    rev = cmp_["ratio_revision"]
    row.update({
        "ratio_revision_median": float(rev.median()),
        "ratio_revision_abs_median": float(rev.abs().median()),
        "ratio_revision_abs_p90": float(rev.abs().quantile(0.9)),
        "h1_revision_rel_median": float(cmp_["h1_revision_rel"].median()),
        "share_h1_revised_up": float((cmp_["h1_revision_rel"] > 0).mean()),
        "share_h1_unchanged": float((cmp_["h1_revision_rel"] == 0).mean()),
    })
    return row


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/experiment.yaml"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args(argv)
    cfg = yaml.safe_load(Path(args.config).read_text())
    out = Path(args.out)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    ks = tuple(cfg["thresholds"])
    k0 = cfg["primary_threshold"]
    summary = {"code_commit": git_sha(), "config_file": str(Path(args.config).name),
               "vintages": [], "blocked": [], "comparisons": {}}

    loaded, inventory = {}, []
    for v in cfg["vintages"]:
        path = Path(v["path"]) if Path(v["path"]).is_absolute() else ROOT / v["path"]
        if not path.exists() or sha256_file(path) != v["sha256"]:
            summary["blocked"].append({"vintage": v["id"], "reason": "file missing or hash mismatch"})
            continue
        raw = preprocess.load_vintage(str(path), v["id"])
        loaded[v["id"]] = (v, raw, raw.attrs["placeholder_rows_dropped"])

    # Region labels for archived snapshots come from the reference (public) file.
    regions = pd.concat([r for _, r, _ in loaded.values()]).dropna(subset=["g_whoregion"]) \
        .drop_duplicates("iso3").set_index("iso3")["g_whoregion"]

    pairs_by_id = {}
    for vid, (v, raw, n_placeholder) in loaded.items():
        raw["g_whoregion"] = raw["g_whoregion"].fillna(raw["iso3"].map(regions))
        h1 = preprocess.h1_totals(raw)
        pairs = evaluate.year_pairs(h1, min_base=cfg["min_base_h1"])
        pairs_by_id[vid] = pairs
        latest = int(raw["year"].max())
        inv = {
            "vintage_id": vid, "source": v.get("source", ""), "nominal_date": v.get("nominal_date", ""),
            "public_by": v["public_by"], "sha256": v["sha256"], "rows": len(raw),
            "placeholder_rows_dropped": n_placeholder, "countries": int(raw["iso3"].nunique()),
            "first_year": int(raw["year"].min()), "latest_year": latest,
            "rows_latest_year": int((raw["year"] == latest).sum()),
            "complete_h1_latest_year": int(h1.loc[h1["year"] == latest, "h1_complete"].sum()),
            "strict_pairs_all_years": int(pairs["strict"].sum()),
            "strict_pairs_latest_year": int(pairs.loc[pairs["year"] == latest, "strict"].sum()),
        }
        for label, key in (("nominal", "nominal_date"), ("public_by", "public_by")):
            try:
                inv[f"h1_latest_maturity_days_{label}"] = audit.h1_maturity_days(
                    latest, date.fromisoformat(str(v.get(key))))
            except ValueError:
                inv[f"h1_latest_maturity_days_{label}"] = np.nan
        inventory.append(inv)
        if v.get("role", "reference") == "reference":
            inv.update(reference_outputs(v, raw, h1, pairs, cfg, out, ks))
        summary["vintages"].append(inv)
    pd.DataFrame(inventory).sort_values("nominal_date").to_csv(out / "tables/vintage_inventory.csv", index=False)

    comps = cfg.get("comparisons")
    if comps is None:  # default: every ordered pair by public-by date
        order = sorted(pairs_by_id, key=lambda i: loaded[i][0]["public_by"])
        comps = [{"id": f"{a}__{b}", "analysis": "all_pairs", "early": a, "late": b, "years": None}
                 for a, b in combinations(order, 2)]

    # Join variants: primary requires identical reporting metadata across vintages.
    variants = [("strict", "identical"), ("relaxed", "identical"), ("strict", "h1_equivalent")]
    rows, units, audits = [], [], []
    for c in comps:
        if c["early"] not in pairs_by_id or c["late"] not in pairs_by_id:
            rows.append({"comparison": c["id"], "analysis": c["analysis"], "status": "NOT_COMPUTABLE",
                         "reason": "vintage missing or hash mismatch"})
            continue
        pa, pb = pairs_by_id[c["early"]], pairs_by_id[c["late"]]
        ve = loaded[c["early"]][0]
        t = (c.get("years") or [None])[0]
        lag = audit.h1_maturity_days(t, date.fromisoformat(ve["public_by"])) if t else np.nan
        for tier in ("strict", "relaxed"):
            aud = evaluate.audit_cross_vintage(pa, pb, tier, c.get("years"))
            audits.append(aud.groupby("status").size().rename("n_units").reset_index().assign(
                comparison=c["id"], analysis=c["analysis"], tier=tier))
        for tier, meta in variants:
            cmp_ = evaluate.compare_vintages(pa, pb, tier, ks, years=c.get("years"), metadata=meta)
            rows.append({"comparison": c["id"], "analysis": c["analysis"], "tier": tier, "metadata_rule": meta,
                         "status": "COMPUTED", "early": c["early"], "late": c["late"], "year_t": t,
                         "early_public_by_lag_days": lag, **summarise_comparison(cmp_, ks)})
            units.append(cmp_.assign(comparison=c["id"], analysis=c["analysis"], tier=tier, metadata_rule=meta))
    if audits:
        pd.concat(audits, ignore_index=True)[["analysis", "comparison", "tier", "status", "n_units"]] \
            .to_csv(out / "tables/cross_vintage_exclusions.csv", index=False)
    comp_table = pd.DataFrame(rows)
    comp_table.to_csv(out / "tables/cross_vintage_comparisons.csv", index=False)
    units_df = pd.concat(units, ignore_index=True) if units else pd.DataFrame()
    if not units_df.empty:
        keep = ["analysis", "comparison", "tier", "metadata_rule", "iso3", "year", *[f"{m}_a" for m in
                evaluate.METADATA], *[f"{m}_b" for m in evaluate.METADATA], "metadata_changed_fields",
                "ratio_a", "ratio_b", "ratio_revision",
                "h1_revision_rel", *[f"changed_{pct(k)}" for k in ks]]
        units_df[keep].to_csv(out / "tables/cross_vintage_units.csv", index=False)

    # Aggregate by analysis (C1 primary): unbalanced, balanced, bootstrap, defer grid.
    agg_rows, boot_rows, defer_rows = [], [], []
    groups = units_df.groupby(["analysis", "tier", "metadata_rule"]) if not units_df.empty else []
    for (analysis, tier, meta), g in groups:
        comps_in = sorted(g["comparison"].unique())
        per_country = g.groupby("iso3")["comparison"].nunique()
        balanced = set(per_country[per_country == len(comps_in)].index)
        for sample, s in (("unbalanced", g), ("balanced", g[g["iso3"].isin(balanced)])):
            if s.empty:
                continue
            label = {"analysis": analysis, "tier": tier, "metadata_rule": meta, "sample": sample}
            agg_rows.append({**label, "n_comparison_groups": len(comps_in),
                             "max_units_per_country": int(s.groupby("iso3").size().max()),
                             **summarise_comparison(s, ks)})
            # Country-cluster uncertainty on the actual revision outcomes.
            stats = {f"share_alert_changed_{pct(k)}": (lambda d, t=pct(k): d[f"changed_{t}"].mean()) for k in ks}
            stats["mean_abs_ratio_revision"] = lambda d: d["ratio_revision"].abs().mean()
            for name, fn in stats.items():
                est, lo, hi = evaluate.cluster_bootstrap(
                    s, fn, n_boot=cfg["bootstrap"]["n_boot"], seed=cfg["seed"], alpha=cfg["bootstrap"]["alpha"])
                boot_rows.append({**label, "statistic": name, "n_units": len(s),
                                  "n_countries": int(s["iso3"].nunique()), "estimate": est,
                                  "ci_low": lo, "ci_high": hi})
            if sample == "unbalanced":
                for k in ks:
                    for b in cfg["defer_buffer_sensitivity"]:
                        for cr in cfg["cost_ratio_grid"]:
                            defer_rows.append({**label, "primary_rule": bool(
                                k == k0 and b == cfg["defer_buffer_primary"] and tier == "strict"
                                and meta == "identical"), **evaluate.defer_rule(s, k, b, cr, 1.0), "cost_ratio": cr})
    agg = pd.DataFrame(agg_rows)
    agg.to_csv(out / "tables/cross_vintage_by_analysis.csv", index=False)
    pd.DataFrame(boot_rows).to_csv(out / "tables/cross_vintage_bootstrap.csv", index=False)
    defer = pd.DataFrame(defer_rows)
    defer.to_csv(out / "tables/defer_rule_grid.csv", index=False)

    status = [{"status": "COMPUTED" if not units_df.empty else "NOT_COMPUTABLE",
               "n_verified_vintages": len(loaded), "n_comparisons": int((comp_table.get("status") == "COMPUTED").sum())
               if not comp_table.empty else 0}]
    pd.DataFrame(status).to_csv(out / "tables/cross_vintage_status.csv", index=False)

    if not units_df.empty and "C1" in set(units_df["analysis"]):
        prim = (units_df["tier"] == "strict") & (units_df["metadata_rule"] == "identical")
        c1 = units_df[(units_df["analysis"] == "C1") & prim]
        figures.revision_scatter(c1, k0, str(out / "figures/c1_revision_scatter.png"))
        s4 = comp_table[(comp_table["analysis"] == "S4") & (comp_table["tier"] == "strict")
                        & (comp_table["metadata_rule"] == "identical")]
        if not s4.empty:
            figures.maturity_curve(s4, k0, str(out / "figures/s4_h1_2021_maturity.png"))
        d = defer[(defer["analysis"] == "C1") & (defer["threshold"] == k0) & (defer["tier"] == "strict")
                  & (defer["metadata_rule"] == "identical")]
        if not d.empty:
            figures.defer_tradeoff(d, str(out / "figures/c1_defer_tradeoff.png"))

    for name, df in (("by_analysis", agg), ("comparisons", comp_table)):
        summary["comparisons"][name] = json.loads(df.to_json(orient="records")) if not df.empty else []
    summary["prior_claim"] = cfg.get("prior_claim")
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    s = main()
    print(json.dumps({"vintages": len(s["vintages"]), "blocked": s["blocked"]}, indent=2))
