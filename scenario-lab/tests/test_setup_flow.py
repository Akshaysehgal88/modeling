"""Check editor conversions and unchanged numerical results across display units."""
from pathlib import Path
import math

import numpy as np
import pytest

from scenario_lab import demo_config, run_model


def app():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import scenario_lab
    return AppTest.from_file(str(Path(scenario_lab.__file__).with_name("app.py"))).run(timeout=30)


def submit(at):
    next(b for b in at.button if b.label == "Run scenario").click().run(timeout=30)
    assert not at.exception and not at.error
    return at.session_state["run"][0]


def edit_table(at, prefix, rows):
    key = next(d.key for d in at.dataframe if d.key and d.key.startswith(prefix))
    at.session_state[key] = {"edited_rows": rows, "added_rows": [], "deleted_rows": []}


@pytest.mark.parametrize("company", ["AMD", "NVDA", "SNDK", "SAMSUNG", "TSMC", "ASML"])
def test_no_edit_submission_preserves_config_and_all_simulation_arrays(company):
    at = app()
    if company != "AMD":
        next(s for s in at.selectbox if s.label == "Company").set_value(company).run(timeout=30)
    assert not at.exception and not at.error
    before = at.session_state["run"][0]
    after = submit(at)
    assert after["config"] == before["config"] == demo_config(company)
    for key in ("paths", "states", "credit", "beliefs", "sentiment_log_residual"):
        np.testing.assert_array_equal(after[key], before[key])
    assert len(at.get("plotly_chart")) == 1
    assert len(at.get("download_button")) == 6


def test_base_eps_case_differences_and_percent_weights_reach_original_engine():
    at = app()
    next(n for n in at.number_input if n.label == "FY2027 adjusted EPS").set_value(20.)
    edit_table(at, "curves_", {0: {"2027": -20.}})
    edit_table(at, "weights_", {0: {"weight": 40.}, 1: {"weight": 40.}})
    edit_table(at, "premiums_", {0: {"adjustment_percent": -20.}})
    result = submit(at)
    expected = demo_config()
    expected["settings"]["eps27"] = 20.
    expected["scenario_eps"]["slowdown"]["2027"] = expected["scenario_eps"]["reference"]["2027"] * .8
    expected["priors"] = [.4, .4, .2]
    expected["regime_log_premiums"][0] = math.log1p(-.2)
    assert result["config"] == expected
    np.testing.assert_array_equal(result["paths"], run_model(expected)["paths"])


def test_blank_monthly_percentile_restores_auto_without_changing_distribution():
    at = app()
    before = at.session_state["run"][0]["paths"].copy()
    edit_table(at, "monthly_regimes_", {4: {"manual_percentile": 80.}})
    assert submit(at)["config"]["monthly_overrides"][5]["manual_percentile"] == 80.
    edit_table(at, "monthly_regimes_", {4: {"manual_percentile": None}})
    result = submit(at)
    assert result["config"]["monthly_overrides"][5]["manual_percentile"] == 0.
    np.testing.assert_array_equal(result["paths"], before)


def test_invalid_starting_weights_show_actionable_error_and_keep_last_run():
    at = app()
    before = at.session_state["run"][0]
    edit_table(at, "weights_", {0: {"weight": 90.}})
    next(b for b in at.button if b.label == "Run scenario").click().run(timeout=30)
    assert not at.exception
    assert any("Starting weights must total 100%" in e.value for e in at.error)
    assert at.session_state["run"][0]["config"] == before["config"]
