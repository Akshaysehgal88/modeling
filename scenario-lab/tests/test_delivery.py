import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scenario_lab import demo_config, run_model, compute_smart_selector
from scenario_lab.report import export_result, html_report


def test_exports_preserve_inputs_overrides_and_provenance(tmp_path):
    c=demo_config(); c["n_paths"]=200
    c["monthly_overrides"][5]["manual_percentile"]=80.
    r=run_model(c); s=compute_smart_selector(r)
    out=export_result(r,s,tmp_path)
    d=pd.read_csv(out/"monthly.csv")
    assert d.classification.iloc[0]=="user_supplied_snapshot"
    assert set(d.classification.iloc[1:])=={"forecast_model_output"}
    assert pd.read_csv(out/"monthly_overrides.csv").manual_percentile.iloc[5]==80
    audit=json.loads((out/"audit.json").read_text())
    assert audit["config"]==c and len(audit["config_sha256"])==64
    assert audit["meta"]["engine"]=="original_v3_preserved"
    assert audit["meta"]["calibration"]["n"]==23
    assert "not independently" in audit["input_provenance"]["event_notes"]
    html=(out/"report.html").read_text(encoding="utf-8")
    assert "<svg" in html and "user_supplied_snapshot" in html
    assert "<script" not in html


def test_custom_text_escaped_in_report():
    c=demo_config(); c["n_paths"]=100
    c["title"]='<script>alert("bad")</script>'
    r=run_model(c); html=html_report(r,compute_smart_selector(r))
    assert "<script" not in html and "&lt;script&gt;" in html


def test_cli_json_and_monthly_csv_round_trip(tmp_path):
    def cli(*args):
        return subprocess.run([sys.executable,"-m","scenario_lab",*map(str,args)],
            capture_output=True,text=True,cwd=tmp_path,timeout=60)
    p=tmp_path/"demo.json"
    assert cli("init",p).returncode==0
    original=p.read_bytes()
    assert cli("init",p).returncode==2 and p.read_bytes()==original
    assert cli("validate",p).returncode==0
    c=json.loads(p.read_text()); c["n_paths"]=200; p.write_text(json.dumps(c))
    controls=pd.DataFrame(c["monthly_overrides"]).iloc[1:].copy()
    controls.loc[7,"manual_percentile"]=80.
    csv=tmp_path/"regimes.csv"; controls.to_csv(csv,index=False)
    result=cli("run","--config",p,"--overrides",csv,"--out",tmp_path/"result")
    assert result.returncode==0,result.stderr
    assert pd.read_csv(tmp_path/"result/selector.csv").smart_percentile.iloc[7]==80
    assert (tmp_path/"result/report.html").is_file()


def test_browser_monthly_editor_reaches_selector_and_downloads():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import scenario_lab
    at=AppTest.from_file(str(Path(scenario_lab.__file__).with_name("app.py"))).run(timeout=30)
    next(s for s in at.selectbox if s.label == "Company").set_value("AMD").run(timeout=30)
    assert not at.exception and not at.error
    before=at.session_state["run"][0]["paths"].copy()
    key=next(d.key for d in at.dataframe if d.key and d.key.startswith("monthly_regimes_"))
    at.session_state[key]={"edited_rows":{4:{"manual_percentile":80.}},"added_rows":[],"deleted_rows":[]}
    next(b for b in at.button if b.label=="Run scenario").click().run(timeout=30)
    assert not at.exception and not at.error
    result,selector=at.session_state["run"]
    assert selector.smart_percentile.iloc[5]==80
    assert result["config"]["monthly_overrides"][5]["manual_percentile"]==80
    np.testing.assert_array_equal(result["paths"],before)
    assert len(at.get("download_button"))==6
    assert len(at.get("plotly_chart"))==1
    next(n for n in at.number_input if n.label=="Peer-market price swing multiplier").set_value(-.1)
    next(b for b in at.button if b.label=="Run scenario").click().run(timeout=30)
    assert not at.exception
    assert any("Peer-market price swing multiplier" in e.value for e in at.error)
