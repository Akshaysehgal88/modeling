from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scenario_lab import demo_config, run_model, compute_smart_selector, list_companies
from scenario_lab.catalog import company_info, get_company
from scenario_lab.config import validate_config
from scenario_lab.currency import for_display, reference_rate
from scenario_lab.report import audit_record, chart_plotly, html_report, output_table
from scenario_lab import _core

IDS = [c["id"] for c in list_companies()]


def test_focus_list_and_instrument_units():
    assert len(IDS) == len(set(IDS)) == 20
    for id in ("NVDA", "SNDK", "SAMSUNG", "SKHYNIX", "TSMC", "ASML"):
        assert id in IDS
    assert get_company("SAMSUNG")["symbol"] == "005930.KS"
    assert get_company("SAMSUNG")["currency"] == "KRW"
    assert get_company("SKHYNIX")["currency"] == "KRW"
    assert get_company("TSMC")["symbol"] == "2330.TW"
    assert get_company("TSMC")["currency"] == "TWD"
    assert get_company("ASML")["symbol"] == "ASML.AS"
    assert get_company("ASML")["currency"] == "EUR"
    assert get_company("ARM")["unit"] == "ADS"
    assert get_company("ARM")["shares_per_unit"] == 1
    with pytest.raises(ValueError, match="Unknown company"):
        demo_config("UNKNOWN")


@pytest.mark.parametrize("id", IDS)
def test_every_preset_is_loadable_and_runs_its_own_inputs(id):
    c = demo_config(id)
    validate_config(c)
    demo_file = Path(__file__).parents[1] / "demos" / f"{id}.json"
    assert json.loads(demo_file.read_text()) == c
    if id != "AMD":
        amd = demo_config()
        assert c["schema_version"] == 3 and c["company"]["id"] == id
        assert c["anchor"]["price"] != amd["anchor"]["price"]
        assert c["scenario_eps"] != amd["scenario_eps"]
        assert c["calibration"]["dataset"] == f"companies/{id}.csv"
        assert all(get_company(id)["name"] in e["catalyst"] for e in c["events"])
        assert c["sources"]["eps_base"]["currency"] == get_company(id)["currency"]
        assert c["forecast_notes"]["classification"] == "forecast_assumption"
    c["n_paths"] = 200
    r = run_model(c)
    s = compute_smart_selector(r)
    assert np.isfinite(r["paths"]).all() and (r["paths"] > 0).all()
    assert (r["paths"][:, 0] == c["anchor"]["price"]).all()
    assert s.smart_percentile.between(10, 90).all()
    if id != "AMD":
        assert r["meta"]["calibration"]["n"] == c["sources"]["history"]["observations"]
    assert company_info(r["config"])["id"] == id


def test_new_inputs_have_separate_disclosures_and_split_basis():
    assert demo_config("SAMSUNG")["sources"]["eps_base"]["value"] == 6603
    assert demo_config("SKHYNIX")["sources"]["eps_base"]["value"] == 60378
    kla = demo_config("KLAC")
    assert kla["sources"]["eps_base"]["value"] == 3.66
    assert "split" in kla["company"]["eps_basis"]
    sndk = demo_config("SNDK")
    assert sndk["sources"]["history"]["observations"] == 19
    assert sndk["calibration"]["window_start"] > "2024-11"


def test_amd_chart_remains_the_original_chart():
    c = demo_config(); c["n_paths"] = 200
    r = run_model(c); s = compute_smart_selector(r)
    view, overlay = for_display(r, s)
    assert chart_plotly(view, overlay).to_json() == _core.chart_plotly(r, selector=s).to_json()
    np.testing.assert_array_equal(view["paths"], r["paths"])


@pytest.mark.parametrize("id", ["NVDA", "SNDK", "SAMSUNG", "TSMC", "ASML"])
def test_currency_conversion_is_presentation_only(id):
    c = demo_config(id); c["n_paths"] = 200
    r = run_model(c); s = compute_smart_selector(r)
    original = r["paths"].copy()
    target = "USD" if c["company"]["currency"] != "USD" else "EUR"
    rate = reference_rate(c["company"]["currency"], target)
    view, selected = for_display(r, s, target)
    np.testing.assert_allclose(view["paths"], original * rate)
    np.testing.assert_array_equal(r["paths"], original)
    np.testing.assert_allclose(selected.selected_price, s.selected_price * rate)
    np.testing.assert_array_equal(selected.percentile, s.percentile)
    np.testing.assert_array_equal(view["monthly"].reference_pe, r["monthly"].reference_pe)
    assert view["config"] == c
    assert audit_record(view, selected)["display"]["currency"] == target
    assert audit_record(view, selected)["instrument"]["id"] == id
    table = output_table(view, selected)
    assert set(table.currency) == {target}
    assert set(table.native_currency) == {c["company"]["currency"]}
    figure = chart_plotly(view, selected)
    assert c["company"]["name"] in figure.layout.title.text
    assert target in figure.layout.yaxis.title.text
    html = html_report(view, selected)
    assert c["company"]["name"] in html and target in html


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), 0, -1, True])
def test_bad_fx_rate_rejected(rate):
    c = demo_config("NVDA"); c["n_paths"] = 100
    r = run_model(c)
    with pytest.raises(ValueError, match="FX rate"):
        for_display(r, compute_smart_selector(r), "EUR", rate)


def test_cross_company_identity_and_data_substitution_rejected():
    c = demo_config("NVDA")
    c["company"]["currency"] = "KRW"
    with pytest.raises(ValueError, match="catalog"):
        validate_config(c)
    c = demo_config("NVDA")
    c["calibration"] = demo_config()["calibration"]
    with pytest.raises(ValueError, match="selected company's"):
        validate_config(c)
    c = demo_config("NVDA")
    c["sources"]["eps_base"] = demo_config("SNDK")["sources"]["eps_base"]
    with pytest.raises(ValueError, match="selected company"):
        validate_config(c)


@pytest.mark.parametrize("problem", ["duplicate", "gap", "nonfinite", "constant_peer"])
def test_company_history_rejects_bad_calibration_pairs(tmp_path, monkeypatch, problem):
    import pandas as pd
    from scenario_lab import market_data
    from importlib.resources import files
    c = demo_config("NVDA")
    with files("scenario_lab").joinpath("data/" + c["calibration"]["dataset"]).open("r") as f:
        frame = pd.read_csv(f)
    if problem == "duplicate":
        frame.loc[1, "month"] = frame.loc[0, "month"]
    elif problem == "gap":
        frame = frame.drop(index=5)
    elif problem == "nonfinite":
        frame.loc[5, "asset_return"] = float("inf")
    else:
        frame["peer_return"] = .01
    target = tmp_path / "data" / c["calibration"]["dataset"]
    target.parent.mkdir(parents=True)
    frame.to_csv(target, index=False)
    monkeypatch.setattr(market_data, "files", lambda package: tmp_path)
    with pytest.raises(ValueError):
        market_data.load_company_history(c)


def test_unicode_labels_are_not_mojibake():
    import scenario_lab
    package = Path(scenario_lab.__file__).parent
    for name in ("app.py", "report.py", "currency.py"):
        content = (package / name).read_text(encoding="utf-8")
        assert "\u00c3\u201a" not in content and "\u00f0\u0178" not in content


def test_new_monthly_regime_override_uses_same_mechanism():
    c = demo_config("SAMSUNG"); c["n_paths"] = 200
    baseline = run_model(c)
    c["monthly_overrides"][5]["manual_percentile"] = 80.
    edited = run_model(c)
    s = compute_smart_selector(edited)
    np.testing.assert_array_equal(edited["paths"], baseline["paths"])
    assert s.smart_percentile.iloc[5] == 80


def test_company_cli_and_currency_exports(tmp_path):
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "scenario_lab", *map(str, args)],
                              cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert len(cli("companies").stdout.splitlines()) == 20
    config = tmp_path / "samsung.json"
    assert cli("init", config, "--company", "SAMSUNG").returncode == 0
    c = json.loads(config.read_text()); c["n_paths"] = 200
    config.write_text(json.dumps(c))
    out = tmp_path / "out"
    result = cli("run", "--config", config, "--currency", "USD", "--out", out)
    assert result.returncode == 0, result.stderr
    audit = json.loads((out / "audit.json").read_text())
    assert audit["config"]["company"]["currency"] == "KRW"
    assert audit["display"]["currency"] == "USD"
    assert cli("run", "--company", "NVDA", "--config", config).returncode == 2


def test_company_switch_keeps_amd_edits_and_cannot_leak_them():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import scenario_lab
    at = AppTest.from_file(str(Path(scenario_lab.__file__).with_name("app.py"))).run(timeout=30)
    assert not at.exception and not at.error
    key = next(d.key for d in at.dataframe if d.key and d.key.startswith("monthly_regimes_"))
    at.session_state[key] = {"edited_rows": {4: {"manual_percentile": 80.}}, "added_rows": [], "deleted_rows": []}
    next(b for b in at.button if b.label == "Run scenario").click().run(timeout=30)
    amd_paths = at.session_state["run"][0]["paths"].copy()
    for id in ("NVDA", "SNDK", "SAMSUNG"):
        next(s for s in at.selectbox if s.label == "Company").set_value(id).run(timeout=30)
        assert not at.exception and not at.error
        c = at.session_state["run"][0]["config"]
        assert c["company"]["id"] == id
        assert c["monthly_overrides"][5]["manual_percentile"] == 0
    native_paths = at.session_state["run"][0]["paths"].copy()
    next(s for s in at.selectbox if s.label == "Display currency").set_value("USD").run(timeout=30)
    assert not at.exception and not at.error
    np.testing.assert_array_equal(at.session_state["run"][0]["paths"], native_paths)
    next(s for s in at.selectbox if s.label == "Company").set_value("AMD").run(timeout=30)
    assert not at.exception and not at.error
    r, selector = at.session_state["run"]
    assert r["config"]["monthly_overrides"][5]["manual_percentile"] == 80
    np.testing.assert_array_equal(r["paths"], amd_paths)
    assert selector.smart_percentile.iloc[5] == 80
