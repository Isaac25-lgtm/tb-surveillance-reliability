import json

import numpy as np
import pandas as pd
import pytest
import yaml
from conftest import monthly, row, write_vintage

from tbvintage import acquire, evaluate, preprocess


def _pairs(df, vid="v1"):
    df = df.assign(vintage_id=vid)
    return evaluate.year_pairs(preprocess.h1_totals(df), min_base=50)


def test_h1_totals_monthly_quarterly_and_missing(synthetic_frame):
    h1 = preprocess.h1_totals(synthetic_frame.assign(vintage_id="v1")).set_index(["iso3", "year"])
    assert h1.loc[("AAA", 2022), "h1_total"] == 540
    assert h1.loc[("FFF", 2021), "h1_total"] == 400
    assert not h1.loc[("DDD", 2022), "h1_complete"]
    assert pd.isna(h1.loc[("DDD", 2022), "h1_total"])  # never a partial sum
    assert h1.loc[("DDD", 2022), "h1_missing_cells"] == 1
    assert h1.loc[("EEE", 2021), "h1_has_zero"]


def test_year_pair_tiers_and_exclusion_reasons(synthetic_frame):
    p = _pairs(synthetic_frame).set_index("iso3")
    assert p.loc["AAA", "strict"] and p.loc["FFF", "strict"]
    assert p.loc["BBB", "exclusion_reason"] == "frequency_change" and not p.loc["BBB", "relaxed"]
    assert p.loc["CCC", "relaxed"] and not p.loc["CCC", "strict"]
    assert p.loc["DDD", "exclusion_reason"] == "incomplete_h1"
    assert p.loc["EEE", "relaxed"] and not p.loc["EEE", "strict"]
    assert p.loc["AAA", "exclusion_reason"] == "included_strict"
    assert p.loc["AAA", "ratio"] == pytest.approx(0.9)


def test_coverage_change_is_not_same_definition(synthetic_frame):
    df = pd.concat([synthetic_frame, pd.DataFrame([row("GGG", 2021, cov=34, h1=monthly(300)),
                                                   row("GGG", 2022, cov=35, h1=monthly(300))])])
    p = _pairs(df).set_index("iso3")
    assert p.loc["GGG", "exclusion_reason"] == "coverage_change"
    assert not p.loc["GGG", "relaxed"]


def test_classify_inclusive_boundary_all_thresholds():
    for k in evaluate.THRESHOLDS:
        r = pd.Series([1 - k, 1 - k + 0.001, np.nan])
        out = evaluate.classify(r, k)
        assert out.iloc[0] == True  # noqa: E712  exactly at threshold counts as decline
        assert out.iloc[1] == False  # noqa: E712
        assert pd.isna(out.iloc[2])


def test_duplicate_keys_rejected(tmp_path, synthetic_frame):
    df = pd.concat([synthetic_frame, synthetic_frame.iloc[[0]]])
    path = write_vintage(df, tmp_path / "dup.csv")
    with pytest.raises(ValueError, match="duplicate"):
        preprocess.load_vintage(str(path), "dup")


def _two_vintages(synthetic_frame):
    early = synthetic_frame.copy()
    late = synthetic_frame.copy()
    # AAA 2022 revised upward 540 -> 570: early alarm at 10% becomes no alarm (false early alarm)
    late.loc[(late.iso3 == "AAA") & (late.year == 2022), [f"m_{i:02d}" for i in range(1, 7)]] = monthly(570)
    # FFF 2022 unchanged (stable)
    # HHH: early 500 -> 480 (no alert), later 2022 revised down to 430 (early miss)
    early = pd.concat([early, pd.DataFrame([row("HHH", 2021, h1=monthly(500)), row("HHH", 2022, h1=monthly(480))])])
    late = pd.concat([late, pd.DataFrame([row("HHH", 2021, h1=monthly(500)), row("HHH", 2022, h1=monthly(430))])])
    return _pairs(early, "early"), _pairs(late, "late")


def test_compare_vintages_counts_reversals(synthetic_frame):
    pa, pb = _two_vintages(synthetic_frame)
    cmp_ = evaluate.compare_vintages(pa, pb, "strict").set_index("iso3")
    assert set(cmp_.index) == {"AAA", "FFF", "HHH"}  # strict in both vintages only
    assert cmp_.loc["AAA", "false_early_alarm_10"] and not cmp_.loc["AAA", "early_miss_10"]
    assert cmp_.loc["HHH", "early_miss_10"]
    assert not cmp_.loc["FFF", "changed_10"]
    assert cmp_.loc["AAA", "h1_revision_rel"] == pytest.approx(570 / 540 - 1)
    assert cmp_["changed_10"].sum() == 2


def test_defer_rule_arithmetic(synthetic_frame):
    pa, pb = _two_vintages(synthetic_frame)
    cmp_ = evaluate.compare_vintages(pa, pb, "strict")
    # early ratios: AAA 0.90, FFF 0.75, HHH 0.96. buffer 0.07 defers AAA and HHH (|0.96-0.9|=0.06)
    res = evaluate.defer_rule(cmp_, 0.10, 0.07, cost_defer=0.2, cost_error=1.0)
    assert res["n_deferred"] == 2
    assert res["errors_if_trust_early"] == 2 and res["errors_after_defer_rule"] == 0
    assert res["loss_defer_rule"] == pytest.approx(0.4) and res["loss_trust_early"] == 2
    assert res["break_even_defer_to_error_cost"] == pytest.approx(1.0)
    none = evaluate.defer_rule(cmp_, 0.10, 0.0)
    assert none["n_deferred"] == 0 and np.isnan(none["break_even_defer_to_error_cost"])


def test_cluster_bootstrap_resamples_whole_countries():
    df = pd.DataFrame({"iso3": ["A"] * 5 + ["B"] * 5, "x": [1.0] * 5 + [0.0] * 5})
    est, lo, hi = evaluate.cluster_bootstrap(df, lambda d: d["x"].mean(), n_boot=300, seed=1)
    assert est == 0.5
    # whole-cluster resampling of 2 countries can only yield 0, 0.5 or 1
    assert lo == 0.0 and hi == 1.0
    again = evaluate.cluster_bootstrap(df, lambda d: d["x"].mean(), n_boot=300, seed=1)
    assert again == (est, lo, hi)
    single = evaluate.cluster_bootstrap(df[df.iso3 == "A"], lambda d: d["x"].mean())
    assert np.isnan(single[1])


def test_manifest_hash_verification(tmp_path):
    f = tmp_path / "v.csv"
    f.write_bytes(b"abc")
    good = acquire.ManifestEntry("v", "u", "t", "t", "own", "200", 3, acquire.sha256_file(f),
                                 "", str(f), "ok")
    assert good.sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    bad = acquire.ManifestEntry(**{**good.__dict__, "vintage_id": "w", "sha256": "0" * 64})
    blocked = acquire.ManifestEntry(**{**good.__dict__, "vintage_id": "x", "outcome": "blocked"})
    m = tmp_path / "m.csv"
    acquire.write_manifest([good, bad, blocked], m)
    entries = acquire.read_manifest(m)
    assert [e.vintage_id for e in acquire.usable_vintages(entries, root="/")] == ["v"]


def test_committed_manifest_records_blocked_attempts():
    from conftest import ROOT
    m = pd.read_csv(ROOT / "data/manifest/source_attempts.csv")
    assert (m.groupby("host").size() <= acquire.MAX_ATTEMPTS_PER_HOST).all()
    ok = m[m.outcome == "ok"]
    assert ok["sha256"].str.fullmatch(r"[0-9a-f]{64}").all() and (ok["bytes"] > 0).all()
    assert set(m.loc[m.host == "web.archive.org", "outcome"]) == {"blocked"}


def test_pipeline_end_to_end_two_synthetic_vintages(tmp_path, synthetic_frame):
    import sys
    from conftest import ROOT
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_pipeline

    early = synthetic_frame
    late = synthetic_frame.copy()
    late.loc[(late.iso3 == "AAA") & (late.year == 2022), [f"m_{i:02d}" for i in range(1, 7)]] = monthly(570)
    pe = write_vintage(early, tmp_path / "raw/early.csv")
    pl = write_vintage(late, tmp_path / "raw/late.csv")
    cfg = yaml.safe_load((ROOT / "configs/experiment.yaml").read_text())
    cfg["vintages"] = [
        {"id": "syn_early", "path": str(pe), "sha256": acquire.sha256_file(pe), "public_by": "2022-10-01"},
        {"id": "syn_late", "path": str(pl), "sha256": acquire.sha256_file(pl), "public_by": "2023-10-01"},
        {"id": "syn_tampered", "path": str(pl), "sha256": "0" * 64, "public_by": "2024-10-01"},
    ]
    cfg["balanced_years"] = [2022]
    cfg["bootstrap"]["n_boot"] = 50
    cp = tmp_path / "cfg.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    s = run_pipeline.main(["--config", str(cp), "--out", str(tmp_path / "out")])
    assert [b["vintage"] for b in s["blocked"]] == ["syn_tampered"]
    status = s["cross_vintage"][0]
    assert status["status"] == "COMPUTED" and status["n_pairs"] == 2 and status["changed_10"] == 1
    rules = pd.read_csv(tmp_path / "out/tables/defer_rule_syn_early__syn_late.csv")
    assert len(rules) == 4 * 4 * 6
    assert json.loads((tmp_path / "out/run_summary.json").read_text())["vintages"][0]["strict_pairs"] == 2
    assert (tmp_path / "out/figures/coverage_syn_early.png").stat().st_size > 1000
