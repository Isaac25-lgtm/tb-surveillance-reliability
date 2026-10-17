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
    # Actual file records (one downloaded file each): positive bytes and a 64-hex SHA-256.
    files = m[(m.outcome == "ok") & m.vintage_id.notna()]
    assert len(files) == 2
    assert files["sha256"].str.fullmatch(r"[0-9a-f]{64}").all() and (files["bytes"] > 0).all()
    assert set(m.loc[m.host == "web.archive.org", "outcome"]) == {"blocked"}
    assert set(m.loc[m.outcome == "empty_response", "bytes"]) == {0}

    g = pd.read_csv(ROOT / "data/manifest/gtb_tme_snapshots.csv")
    assert g["sha256"].str.fullmatch(r"[0-9a-f]{64}").all() and (g["bytes"] > 0).all()
    assert g["git_blob_sha1"].str.fullmatch(r"[0-9a-f]{40}").all()
    assert g["commit"].str.fullmatch(r"[0-9a-f]{40}").all()
    assert g["vintage_id"].is_unique and len(g) == 17
    assert g["duplicate_of"].dropna().isin(g["vintage_id"]).all()
    # public-by is the commit date, never the nominal snapshot date in the file name
    assert (g["public_by_utc"] == g["commit_date_utc"]).all()

    # Batch operations (no single file): they carry no hash/bytes of their own, and any file
    # reference must resolve to the snapshot manifest's file records.
    batch = m[(m.outcome == "ok") & m.vintage_id.isna()]
    assert len(batch) == 3 and (batch["bytes"] == 0).all()
    assert set(batch["host"]) == {"github.com (git)"}
    refs = batch[batch["sha256"].notna()]
    assert set(refs["sha256"]) == {"see gtb_tme_snapshots.csv"}
    assert refs["source_url"].str.contains(f"for {len(g)} monthly").all()
    assert set(refs["local_path"]) == {"data/raw/gtb_tme/"}

    # Every archived vintage in the config is pinned to the manifest hash for its path.
    cfg = yaml.safe_load((ROOT / "configs/experiment.yaml").read_text())
    by_path = {f"data/raw/gtb_tme/{r.repo.split('/')[1]}/{r.path}": r.sha256 for r in g.itertuples()}
    archived = [v for v in cfg["vintages"] if v["role"] == "archive"]
    assert len(archived) == g["duplicate_of"].isna().sum()
    assert all(by_path[v["path"]] == v["sha256"] for v in archived)


def test_read_snapshot_harmonises_internal_schema(tmp_path):
    from tbvintage.preprocess import read_snapshot
    f = tmp_path / "monthly_2021-01-01.csv"
    hdr = ["country", "iso2", "iso3", "year", "report.frequency", "report.coverage",
           *[f"m.{i:02d}" for i in range(1, 13)], *[f"q.{i}" for i in range(1, 5)], "gaps.na", "remarks"]
    rows = [["X", "XX", "XXX", 2021, 70, 34, *range(1, 13), *[""] * 4, 0, "contact Jane Doe"],
            ["Y", "YY", "YYY", 2021, 70, "", *[""] * 16, "", ""]]
    f.write_text("\n".join(",".join(map(str, r)) for r in [hdr, *rows]), encoding="latin-1")
    df, dropped = read_snapshot(str(f))
    assert dropped == 1 and list(df["iso3"]) == ["XXX"]
    assert "remarks" not in df.columns and "gaps_na" not in df.columns
    assert df.loc[0, "m_06"] == 6 and df["g_whoregion"].isna().all()


def _variant(early, mutate):
    late = early.copy()
    mutate(late)
    return _pairs(early, "early"), _pairs(late, "late")


def _set_h1(df, iso3, year, **cells):
    idx = (df.iso3 == iso3) & (df.year == year)
    for k, v in cells.items():
        df.loc[idx, k] = v


def test_frequency_switch_between_releases_excluded_from_primary(synthetic_frame):
    """AAA monthly in the early release, re-issued as quarterly (same H1 totals) later."""
    def mutate(df):
        for year, tot in ((2021, 600), (2022, 540)):
            idx = (df.iso3 == "AAA") & (df.year == year)
            df.loc[idx, [f"m_{i:02d}" for i in range(1, 13)]] = None
            df.loc[idx, ["report_frequency", "q_1", "q_2"]] = [71, tot / 2, tot / 2]
    pa, pb = _variant(synthetic_frame, mutate)
    aud = evaluate.audit_cross_vintage(pa, pb, "strict").set_index("iso3")
    assert aud.loc["AAA", "status"] == "metadata_changed:report_frequency+report_frequency_prev"
    assert aud.loc["FFF", "status"] == "included"
    prim = evaluate.compare_vintages(pa, pb, "strict", metadata="identical")
    sens = evaluate.compare_vintages(pa, pb, "strict", metadata="h1_equivalent")
    assert "AAA" not in set(prim.iso3) and "AAA" in set(sens.iso3)
    assert sens.set_index("iso3").loc["AAA", "report_frequency_b"] == 71
    assert sens.set_index("iso3").loc["AAA", "ratio_revision"] == pytest.approx(0)


def test_frequency_switch_in_one_year_of_late_release_fails_tier(synthetic_frame):
    """Late release switches only year t to quarterly: internally a frequency change."""
    def mutate(df):
        idx = (df.iso3 == "AAA") & (df.year == 2022)
        df.loc[idx, [f"m_{i:02d}" for i in range(1, 13)]] = None
        df.loc[idx, ["report_frequency", "q_1", "q_2"]] = [71, 270, 270]
    pa, pb = _variant(synthetic_frame, mutate)
    aud = evaluate.audit_cross_vintage(pa, pb, "strict").set_index("iso3")
    assert aud.loc["AAA", "status"] == "not_strict_in_late:frequency_change"
    for meta in evaluate.METADATA_RULES:
        assert "AAA" not in set(evaluate.compare_vintages(pa, pb, "strict", metadata=meta).iso3)


def test_coverage_downgrade_in_late_release_is_audited(synthetic_frame):
    def mutate(df):
        _set_h1(df, "FFF", 2022, report_coverage=35)
    pa, pb = _variant(synthetic_frame, mutate)
    aud = evaluate.audit_cross_vintage(pa, pb, "strict").set_index("iso3")
    assert aud.loc["FFF", "status"] == "not_strict_in_late:coverage_change"
    assert "FFF" not in set(evaluate.compare_vintages(pa, pb, "strict", metadata="h1_equivalent").iso3)


def test_relaxed_tier_coverage_code_change_across_releases(synthetic_frame):
    """CCC is some-units (35) early; later release recodes both years as missing coverage."""
    def mutate(df):
        df.loc[df.iso3 == "CCC", "report_coverage"] = np.nan
    pa, pb = _variant(synthetic_frame, mutate)
    aud = evaluate.audit_cross_vintage(pa, pb, "relaxed").set_index("iso3")
    assert aud.loc["CCC", "status"] == "metadata_changed:report_coverage+report_coverage_prev"
    assert "CCC" not in set(evaluate.compare_vintages(pa, pb, "relaxed").iso3)
    assert "CCC" in set(evaluate.compare_vintages(pa, pb, "relaxed", metadata="h1_equivalent").iso3)


def test_missing_coverage_in_both_releases_counts_as_identical(synthetic_frame):
    df = synthetic_frame.copy()
    df.loc[df.iso3 == "CCC", "report_coverage"] = np.nan
    pa, pb = _pairs(df, "early"), _pairs(df, "late")
    assert evaluate.audit_cross_vintage(pa, pb, "relaxed").set_index("iso3").loc["CCC", "status"] == "included"


def test_absent_and_late_only_units_are_reported_not_joined(synthetic_frame):
    late = synthetic_frame[synthetic_frame.iso3 != "FFF"].copy()
    _set_h1(late, "DDD", 2022, m_05=50)  # DDD becomes complete (strict) only in the late release
    pa, pb = _pairs(synthetic_frame, "early"), _pairs(late, "late")
    aud = evaluate.audit_cross_vintage(pa, pb, "strict").set_index("iso3")
    assert aud.loc["FFF", "status"] == "absent_in_late"
    assert aud.loc["DDD", "status"] == "not_strict_in_early:incomplete_h1"
    joined = evaluate.compare_vintages(pa, pb, "strict")
    assert set(joined.iso3) == {"AAA"}
    with pytest.raises(ValueError):
        evaluate.compare_vintages(pa, pb, "strict", metadata="anything")


def test_pipeline_end_to_end_two_synthetic_vintages(tmp_path, synthetic_frame):
    import sys
    from conftest import ROOT
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_pipeline

    early = synthetic_frame
    late = synthetic_frame.copy()
    late.loc[(late.iso3 == "AAA") & (late.year == 2022), [f"m_{i:02d}" for i in range(1, 7)]] = monthly(570)
    # FFF re-issued with a different frequency in the late release (same H1 totals)
    for year, tot in ((2021, 400), (2022, 300)):
        idx = (late.iso3 == "FFF") & (late.year == year)
        late.loc[idx, ["q_1", "q_2"]] = None
        late.loc[idx, ["report_frequency", *[f"m_{i:02d}" for i in range(1, 7)]]] = [70, *monthly(tot)]
    pe = write_vintage(early, tmp_path / "raw/early.csv")
    pl = write_vintage(late, tmp_path / "raw/late.csv")
    cfg = yaml.safe_load((ROOT / "configs/experiment.yaml").read_text())
    cfg["vintages"] = [
        {"id": "syn_early", "path": str(pe), "sha256": acquire.sha256_file(pe), "public_by": "2022-10-01",
         "nominal_date": "2022-09-01", "role": "reference"},
        {"id": "syn_late", "path": str(pl), "sha256": acquire.sha256_file(pl), "public_by": "2023-10-01",
         "nominal_date": "2023-09-01", "role": "archive"},
        {"id": "syn_tampered", "path": str(pl), "sha256": "0" * 64, "public_by": "2024-10-01"},
    ]
    cfg["comparisons"] = [{"id": "C1_2022", "analysis": "C1", "early": "syn_early", "late": "syn_late",
                           "years": [2022]}]
    cfg["balanced_years"] = [2022]
    cfg["bootstrap"]["n_boot"] = 50
    cp = tmp_path / "cfg.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    s = run_pipeline.main(["--config", str(cp), "--out", str(tmp_path / "out")])
    assert [b["vintage"] for b in s["blocked"]] == ["syn_tampered"]
    t = pd.read_csv(tmp_path / "out/tables/cross_vintage_comparisons.csv").set_index(["tier", "metadata_rule"])
    assert t.loc[("strict", "identical"), "n_units"] == 1  # FFF excluded: frequency differs by release
    assert t.loc[("strict", "identical"), "changed_10"] == 1
    assert t.loc[("strict", "h1_equivalent"), "n_units"] == 2
    ex = pd.read_csv(tmp_path / "out/tables/cross_vintage_exclusions.csv")
    ex = ex[ex.tier == "strict"].set_index("status")["n_units"]
    assert ex["included"] == 1
    assert ex["metadata_changed:report_frequency+report_frequency_prev"] == 1
    boot = pd.read_csv(tmp_path / "out/tables/cross_vintage_bootstrap.csv")
    assert {"share_alert_changed_10", "mean_abs_ratio_revision"} <= set(boot.statistic)
    rules = pd.read_csv(tmp_path / "out/tables/defer_rule_grid.csv")
    assert rules["primary_rule"].sum() == 6  # one per cost ratio
    assert (tmp_path / "out/figures/c1_revision_scatter.png").stat().st_size > 1000


def test_cluster_bootstrap_matches_concat_reference():
    """Fast positional resampling must reproduce the whole-country concat resampler exactly."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"iso3": rng.choice(list("ABCDEFG"), 60), "x": rng.normal(size=60)})
    df = df.sample(frac=1, random_state=1)  # non-contiguous, unsorted index

    def reference(d, stat, n_boot, seed):
        r = np.random.default_rng(seed)
        groups = {c: g for c, g in d.groupby("iso3")}
        ids = np.array(list(groups))
        draws = [stat(pd.concat([groups[c] for c in r.choice(ids, size=len(ids), replace=True)],
                                ignore_index=True)) for _ in range(n_boot)]
        return tuple(np.nanquantile(draws, [0.025, 0.975]))

    stat = lambda d: d["x"].mean() + 0.1 * d["x"].iloc[0]  # noqa: E731  order-sensitive on purpose
    _, lo, hi = evaluate.cluster_bootstrap(df, stat, n_boot=200, seed=9)
    assert (lo, hi) == pytest.approx(reference(df, stat, 200, 9), abs=1e-12)
