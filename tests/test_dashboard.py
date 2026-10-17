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
