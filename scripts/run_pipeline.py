"""Run the R02 checkpoint pipeline on every hash-verified vintage in configs/experiment.yaml.

Usage: python scripts/run_pipeline.py [--config configs/experiment.yaml] [--out results]
Raw files are read from data/raw/ (git-ignored); only aggregate outputs are written.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tbvintage import audit, evaluate, figures, preprocess  # noqa: E402
from tbvintage.acquire import sha256_file  # noqa: E402


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


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
    summary = {"code_commit": git_sha(), "config": cfg, "vintages": [], "blocked": []}

    pairs_by_vintage = {}
    for v in cfg["vintages"]:
        path = ROOT / v["path"]
        if not path.exists() or sha256_file(path) != v["sha256"]:
            summary["blocked"].append({"vintage": v["id"], "reason": "file missing or hash mismatch"})
            continue
        raw = preprocess.load_vintage(str(path), v["id"])
        h1 = preprocess.h1_totals(raw)
        pairs = evaluate.year_pairs(h1, min_base=cfg["min_base_h1"])
        pairs_by_vintage[v["id"]] = (v, pairs)
        vid = v["id"]
        vdate = date.fromisoformat(v["public_by"])

        cov = audit.coverage_by_year(raw, h1)
        cov["h1_maturity_days_at_vintage"] = [audit.h1_maturity_days(int(y), vdate) for y in cov["year"]]
        cov.to_csv(out / f"tables/coverage_by_year_{vid}.csv", index=False)

        flow = pairs.groupby(["year", "exclusion_reason"]).size().unstack(fill_value=0)
        flow["strict"] = pairs.groupby("year")["strict"].sum()
        flow["relaxed"] = pairs.groupby("year")["relaxed"].sum()
        flow["pairs_with_both_years_present"] = pairs.groupby("year").size()
        flow = flow.reset_index()
        flow.to_csv(out / f"tables/pair_flow_{vid}.csv", index=False)

        bal = evaluate.balanced_countries(pairs, cfg["balanced_years"], "strict")
        pairs["balanced"] = pairs["strict"] & pairs["iso3"].isin(bal)
        thr = pd.concat([evaluate.threshold_summary(pairs, t, ks) for t in ("strict", "relaxed", "balanced")])
        thr.to_csv(out / f"tables/threshold_counts_{vid}.csv", index=False)

        cols = ["iso3", "country", "g_whoregion", "year", "report_frequency", "h1_total_prev", "h1_total", "ratio"]
        pairs.loc[pairs["strict"], cols].sort_values(["year", "iso3"]).to_csv(
            out / f"tables/h1_ratios_strict_{vid}.csv", index=False)

        strict = pairs[pairs["strict"]]
        k0 = cfg["primary_threshold"]
        boot = []
        for name, df in (("all_strict_pairs", strict),
                         ("balanced_strict_pairs", strict[strict["iso3"].isin(bal)])):
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

        summary["vintages"].append({
            "id": vid, "sha256": v["sha256"], "rows": len(raw), "countries": int(raw["iso3"].nunique()),
            "years": [int(raw["year"].min()), int(raw["year"].max())],
            "strict_pairs": int(pairs["strict"].sum()), "relaxed_pairs": int(pairs["relaxed"].sum()),
            "strict_countries": int(strict["iso3"].nunique()), "balanced_countries": len(bal),
            "complete_h1_latest_year": int(h1.loc[h1["year"] == h1["year"].max(), "h1_complete"].sum()),
        })

    # Cross-vintage revision analysis needs >= 2 verified vintages.
    ordered = sorted(pairs_by_vintage.values(), key=lambda t: t[0]["public_by"])
    status = []
    if len(ordered) < 2:
        status.append({"status": "NOT_COMPUTABLE", "n_verified_vintages": len(ordered),
                       "reason": "only one verified vintage; archived releases blocked or absent"})
    for (va, pa), (vb, pb) in combinations(ordered, 2):
        cmp_ = evaluate.compare_vintages(pa, pb, "strict", ks)
        tag = f"{va['id']}__{vb['id']}"
        cmp_.to_csv(out / f"tables/cross_vintage_{tag}.csv", index=False)
        rules = [evaluate.defer_rule(cmp_, k, b, c, 1.0)
                 for k in ks for b in cfg["defer_buffer_sensitivity"] for c in cfg["cost_ratio_grid"]]
        pd.DataFrame(rules).to_csv(out / f"tables/defer_rule_{tag}.csv", index=False)
        status.append({"status": "COMPUTED", "early": va["id"], "late": vb["id"], "n_pairs": len(cmp_),
                       "n_countries": int(cmp_["iso3"].nunique()),
                       **{f"changed_{int(k * 100)}": int(cmp_[f"changed_{int(k * 100)}"].sum()) for k in ks}})
    pd.DataFrame(status).to_csv(out / "tables/cross_vintage_status.csv", index=False)
    summary["cross_vintage"] = status
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    s = main()
    print(json.dumps({k: s[k] for k in ("vintages", "blocked", "cross_vintage")}, indent=2))
