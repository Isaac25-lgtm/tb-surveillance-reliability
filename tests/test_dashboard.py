import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "dashboard" / "app.py")
testing = pytest.importorskip("streamlit.testing.v1")


def _app(monkeypatch, full: bool):
    if full:
        monkeypatch.setenv("R02_SHOW_ARCHIVE_DERIVED", "1")
    else:
        monkeypatch.delenv("R02_SHOW_ARCHIVE_DERIVED", raising=False)
    return testing.AppTest.from_file(APP, default_timeout=60).run()


@pytest.mark.parametrize("full", [False, True])
def test_every_page_renders(monkeypatch, full):
    at = _app(monkeypatch, full)
    assert not at.exception
    decision = re.search(r"Overall\W+\*\*([A-Z_]+)\*\*", (ROOT / "docs/STATUS.md").read_text()).group(1)
    assert decision in at.info[0].value and "not by WHO" in at.info[0].value
    pages = at.sidebar.radio[0].options
    assert ("Alert reversals" in pages) == full and ("Defer rule" in pages) == full
    for p in pages:
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, p


def test_default_scope_withholds_archive_results(monkeypatch):
    at = _app(monkeypatch, False)
    assert any("HOLD_DEPLOYMENT" in w.value for w in at.warning)
    assert not any("89" in m.value for m in at.metric)


def test_primary_metrics_and_filters(monkeypatch):
    at = _app(monkeypatch, True)
    vals = {m.label: m.value for m in at.metric}
    assert vals["Comparable country-years (C1)"] == "89" and vals["Independent countries"] == "52"
    assert vals["Alerts changed at -10%"] == "3 / 89" and vals["Stable at -10%"] == "86"
    at.sidebar.radio[0].set_value("Alert reversals").run()
    sel = {s.label: s for s in at.selectbox}
    sel["Tier"].set_value("relaxed").run()
    vals = {m.label: m.value for m in at.metric}
    assert vals["Country-years"] == "125" and vals["Changed at -10%"] == "8"
    sel = {s.label: s for s in at.selectbox}
    sel["Decline threshold (%)"].set_value(20).run()
    assert {m.label: m.value for m in at.metric}["Changed at -20%"] == "2"
    sel = {s.label: s for s in at.selectbox}
    sel["Country (ISO3)"].set_value("TZA").run()
    assert not at.exception


@pytest.mark.parametrize("full", [False, True])
def test_downloads_are_allowlisted(monkeypatch, full):
    import sys
    sys.path.insert(0, str(ROOT / "dashboard"))
    from safety import NEVER_DOWNLOAD, allowed_downloads

    at = _app(monkeypatch, full)
    at.sidebar.radio[0].set_value("Downloads").run()
    assert not at.exception
    names = set(allowed_downloads(full))
    labels = [b.proto.label for b in at.get("download_button")]
    assert len(labels) == len(names) > 0
    assert all(any(lbl.startswith(n) for n in names) for lbl in labels)
    assert not NEVER_DOWNLOAD & names
    assert all(n.endswith((".csv", ".png")) for n in names)
    assert ("cross_vintage_by_analysis.csv" in names) == full


def _reversals(monkeypatch, **choices):
    at = _app(monkeypatch, True)
    at.sidebar.radio[0].set_value("Alert reversals").run()
    for label, value in choices.items():
        {s.label: s for s in at.selectbox}[label].set_value(value).run()
    assert not at.exception
    return at


def _chart_counts(at):
    cap = next(c.value for c in at.caption if c.value.startswith("Chart sample"))
    n, k = map(int, re.search(r"(\d+) country-years from (\d+) countries", cap).groups())
    tables = [d.value for d in at.dataframe]
    changed, stable = tables[-2], tables[-1]  # changed / stable lists are the last two tables
    return n, k, len(changed) + len(stable), changed["iso3"].nunique() + 0, set(changed.iso3) | set(stable.iso3)


@pytest.mark.parametrize("sample, n, k, n_changed", [("unbalanced", 89, 52, 3), ("balanced", 16, 4, 0)])
def test_reversal_chart_uses_same_sample_as_summary(monkeypatch, sample, n, k, n_changed):
    at = _reversals(monkeypatch, Sample=sample)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Country-years"] == str(n) and metrics["Independent countries"] == str(k)
    n_chart, k_chart, n_tables, _, countries = _chart_counts(at)
    assert (n_chart, k_chart, n_tables, len(countries)) == (n, k, n, k)
    assert len(at.dataframe[-2].value) == n_changed == int(metrics["Changed at -10%"])


def test_balanced_sample_matches_pipeline_definition(monkeypatch):
    import pandas as pd
    u = pd.read_csv(ROOT / "results/tables/cross_vintage_units.csv")
    u = u[(u.analysis == "C1") & (u.tier == "strict") & (u.metadata_rule == "identical")]
    per = u.groupby("iso3")["comparison"].nunique()
    expected = set(per[per == u.comparison.nunique()].index)
    at = _reversals(monkeypatch, Sample="balanced")
    assert _chart_counts(at)[4] == expected


def test_s3_scatter_labels_next_report_reference(monkeypatch):
    at = _reversals(monkeypatch, Analysis="S3")
    spec = json.dumps([c.proto.spec for c in at.get("vega_lite_chart")])
    assert "next year's report snapshot" in spec and "2026-10-17 public file" not in spec
    refs = set(at.dataframe[-1].value.reference_file) | set(at.dataframe[-2].value.reference_file)
    assert refs and all(r.startswith("gtb20") for r in refs)


def test_overview_defer_sentence_comes_from_data(monkeypatch):
    import pandas as pd
    g = pd.read_csv(ROOT / "results/tables/defer_rule_grid.csv")
    pr = g[g.primary_rule & (g.analysis == "C1")].iloc[0]
    at = _app(monkeypatch, True)
    text = " ".join(m.value for m in at.markdown)
    assert f"deferred {int(pr.n_deferred)} of {int(pr.n_decisions)} decisions and avoided " \
           f"{int(pr.errors_avoided)} reversals" in text
