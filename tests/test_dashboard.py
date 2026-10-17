from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_renders_from_committed_aggregates():
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert "HOLD_ACCESS" in at.info[0].value
    assert any("Not computable" in w.value for w in at.warning)
