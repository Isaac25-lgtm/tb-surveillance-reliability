"""Integrity of the committed aggregate results (no recomputation, no network)."""

import csv
import hashlib
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "results" / "tables"


def test_results_match_manifest():
    with open(ROOT / "results/RESULTS_MANIFEST.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 19  # 13 tables, 5 figures, run_summary.json
    for r in rows:
        data = (ROOT / r["path"]).read_bytes()
        assert len(data) == int(r["bytes"]), r["path"]
        assert hashlib.sha256(data).hexdigest() == r["sha256"], r["path"]


def _primary():
    a = pd.read_csv(T / "cross_vintage_by_analysis.csv")
    return a[(a.analysis == "C1") & (a.tier == "strict") & (a.metadata_rule == "identical")
             & (a["sample"] == "unbalanced")].iloc[0]


def test_headline_numbers():
    p = _primary()
    assert (p.n_units, p.n_countries, p.changed_10) == (89, 52, 3)
    assert p.n_units - p.changed_10 == 86
    assert (p.false_early_alarm_10, p.early_miss_10) == (3, 0)
    assert [p[f"changed_{k}"] for k in (5, 10, 15, 20)] == [5, 3, 2, 1]
    a = pd.read_csv(T / "cross_vintage_by_analysis.csv")
    rel = a[(a.analysis == "C1") & (a.tier == "relaxed") & (a.metadata_rule == "identical")
            & (a["sample"] == "unbalanced")].iloc[0]
    assert (rel.n_units, rel.changed_10) == (125, 8)
    b = pd.read_csv(T / "cross_vintage_bootstrap.csv")
    ci = b[(b.analysis == "C1") & (b.tier == "strict") & (b.metadata_rule == "identical")
           & (b["sample"] == "unbalanced") & (b.statistic == "share_alert_changed_10")].iloc[0]
    assert ci.estimate == pytest.approx(3 / 89)
    assert ci.ci_low == 0 and ci.ci_high == pytest.approx(0.0761, abs=5e-4)
    d = pd.read_csv(T / "defer_rule_grid.csv")
    rule = d[d.primary_rule & (d.analysis == "C1")]
    assert set(rule.n_deferred) == {14} and set(rule.errors_avoided) == {3}


def test_tables_are_mutually_consistent():
    u = pd.read_csv(T / "cross_vintage_units.csv")
    a = pd.read_csv(T / "cross_vintage_by_analysis.csv")
    for (an, tier, meta), g in u.groupby(["analysis", "tier", "metadata_rule"]):
        r = a[(a.analysis == an) & (a.tier == tier) & (a.metadata_rule == meta) & (a["sample"] == "unbalanced")]
        assert len(r) == 1 and int(r.n_units.iloc[0]) == len(g)
        for k in (5, 10, 15, 20):
            assert int(r[f"changed_{k}"].iloc[0]) == int(g[f"changed_{k}"].sum())
    ex = pd.read_csv(T / "cross_vintage_exclusions.csv")
    c = pd.read_csv(T / "cross_vintage_comparisons.csv")
    inc = ex[ex.status == "included"].set_index(["comparison", "tier"])["n_units"]
    for _, r in c[c.metadata_rule == "identical"].iterrows():
        assert inc.get((r.comparison, r.tier), 0) == r.n_units


def test_no_free_text_names_or_emails_in_outputs():
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for p in list(T.glob("*.csv")) + [ROOT / "results/run_summary.json"]:
        text = p.read_text()
        assert "remarks" not in text.lower(), p
        assert not email.search(text), p
    for p in T.glob("*.csv"):
        assert not {"remarks", "gaps_na", "gaps.na"} & set(pd.read_csv(p, nrows=0).columns), p
