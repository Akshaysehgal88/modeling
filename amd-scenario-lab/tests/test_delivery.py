import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from amd_scenario_lab import demo_config, run_model, compute_smart_selector
from amd_scenario_lab.report import export_result, html_report


def test_exports_include_classifications_sources_and_reproducible_audit(tmp_path):
    c = demo_config()
    c["n_paths"] = 200
    r = run_model(c)
    s = compute_smart_selector(r)
    out = export_result(r, s, tmp_path)
    d = pd.read_csv(out / "monthly.csv")
    assert d.classification.iloc[0] == "synthetic_demo"
    assert set(d.classification.iloc[1:]) == {"forecast_model_output"}
    diagnostics = pd.read_csv(out / "selector.csv")
    assert diagnostics.classification.iloc[0] == "synthetic_demo"
    a = json.loads((out / "audit.json").read_text())
    assert a["config"] == c
    assert len(a["config_sha256"]) == 64
    assert a["public_facts"]["facts"][0]["source_url"].startswith("https://ir.amd.com/")
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "<svg" in html and "not calibrated" in html and "synthetic_demo" in html
    assert "<script" not in html and "<iframe" not in html


def test_custom_text_escaped_in_report():
    c = demo_config()
    c["n_paths"] = 100
    c["title"] = '<script>alert("bad")</script>'
    c["anchor"]["note"] = "<img src=x onerror=alert(1)>"
    r = run_model(c)
    html = html_report(r, compute_smart_selector(r))
    assert "<script" not in html and "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_installed_cli_init_validate_run_and_overwrite_protection(tmp_path):
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "amd_scenario_lab", *map(str, args)],
                              capture_output=True, text=True, cwd=tmp_path, timeout=60)
    config = tmp_path / "scenario.json"
    assert cli("init", config).returncode == 0
    original = config.read_bytes()
    assert cli("init", config).returncode == 2
    assert config.read_bytes() == original
    assert cli("validate", config).returncode == 0
    run = cli("run", "--config", config, "--out", tmp_path / "outputs")
    assert run.returncode == 0, run.stderr
    assert "synthetic_demo" in run.stdout
    assert (tmp_path / "outputs" / "report.html").is_file()


def test_browser_form_run_and_validation():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import amd_scenario_lab
    app_path = Path(amd_scenario_lab.__file__).with_name("app.py")
    at = AppTest.from_file(str(app_path)).run(timeout=30)
    assert not at.exception
    next(b for b in at.button if b.label == "Run scenario").click().run(timeout=30)
    assert not at.exception and not at.error
    assert len(at.get("plotly_chart")) == 1
    assert len(at.get("download_button")) == 5
    next(t for t in at.text_input if t.label.startswith("Starting month")).set_value("bad")
    next(b for b in at.button if b.label == "Run scenario").click().run(timeout=30)
    assert not at.exception
    assert any("start_month" in e.value for e in at.error)
