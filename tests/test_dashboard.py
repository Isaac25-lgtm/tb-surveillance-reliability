import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_renders_from_committed_aggregates():
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=60).run()
    assert not at.exception
    decision = re.search(r"Overall: \*\*([A-Z_]+)\*\*", (ROOT / "docs/STATUS.md").read_text()).group(1)
    assert decision in at.info[0].value
    status = pd.read_csv(ROOT / "results/tables/cross_vintage_status.csv")
    not_computable = not (status["status"] == "COMPUTED").any()
    assert any("Not computable" in w.value for w in at.warning) == not_computable
