from dataclasses import asdict
import json
from pathlib import Path

import pytest

from amd_scenario_lab.config import demo_config, load_config, public_facts, validate_config
from amd_scenario_lab._core import Settings


@pytest.mark.parametrize("path,value", [
    (("n_paths",),0), (("n_paths",),True), (("seed",),-1), (("horizon_months",),12),
    (("start_month",),"2026-13"), (("anchor","price"),float("nan")),
    (("anchor","price"),float("inf")), (("settings","peer_shock_scale"),-.1),
    (("settings","initial_regime"),.5), (("settings","credit_persistence"),1.1),
    (("priors",),[.1,.1,.1]), (("selector","path_index"),6000),
    (("selector","condition_strength"),float("nan")), (("anchor","as_of"),"bad"),
    (("calibration","classification"),"public_disclosed_fact")])

def test_invalid_inputs_rejected(path,value):
    c=demo_config(); obj=c
    for key in path[:-1]: obj=obj[key]
    obj[path[-1]]=value
    with pytest.raises(ValueError): validate_config(c)


def test_unknown_fields_and_personal_finance_fields_not_accepted():
    c=demo_config(); c["unexpected"]=1
    with pytest.raises(ValueError,match="expected fields"): validate_config(c)
    forbidden={"share_count","inr_per_usd","proceeds_net_fraction","target_net_crore","target_sale_shares"}
    assert not forbidden.intersection(asdict(Settings()))
    assert not any(key in json.dumps(demo_config()) for key in forbidden)


def test_public_anchor_still_requires_source_and_matching_date():
    c=demo_config(); c["anchor"]["classification"]="public_observation"
    with pytest.raises(ValueError,match="source_url"): validate_config(c)
    c["anchor"]["source_url"]="https://example.com/quote"
    c["anchor"]["as_of"]="2025-01-01"
    with pytest.raises(ValueError,match="start_month"): validate_config(c)


@pytest.mark.parametrize("field,value",[("market_condition","Unknown"),("manual_percentile",5.),("manual_percentile",95.)])
def test_invalid_monthly_choices_rejected(field,value):
    c=demo_config(); c["monthly_overrides"][3][field]=value
    with pytest.raises(ValueError): validate_config(c)


def test_missing_months_duplicates_and_anchor_override_rejected():
    c=demo_config(); c["events"][1]["month"]=c["events"][0]["month"]
    with pytest.raises(ValueError,match="each forecast month"): validate_config(c)
    c=demo_config(); c["monthly_overrides"][0]["manual_percentile"]=80.
    with pytest.raises(ValueError,match="initial anchor"): validate_config(c)


def test_nonpositive_adjusted_eps_rejected():
    c=demo_config(); c["scenario_eps"]["slowdown"]["2028"]=.001
    c["settings"]["earnings_scenario_spread"]=2.
    with pytest.raises(ValueError,match="nonpositive"): validate_config(c)


def test_json_nonfinite_rejected(tmp_path):
    c=demo_config(); c["anchor"]["price"]=float("nan")
    p=tmp_path/"bad.json"; p.write_text(json.dumps(c),encoding="utf-8")
    with pytest.raises(ValueError,match="Nonfinite"): load_config(p)


def test_provenance_and_packaged_data_allowlist():
    for fact in public_facts()["facts"]:
        assert fact["classification"]=="public_disclosed_fact"
        assert fact["source_url"].startswith("https://ir.amd.com/")
    c=demo_config()
    assert c["anchor"]["classification"]=="user_supplied_snapshot"
    assert c["calibration"]["classification"]=="user_supplied_model_input"
    assert all(e["classification"]=="forecast_assumption" for e in c["events"])
    data=Path(__file__).parents[1]/"src/amd_scenario_lab/data"
    assert {p.name for p in data.iterdir() if p.is_file()}=={"demo.json","public_facts.json","amd_peer_history.csv"}
    standalone=Path(__file__).parents[1]/"demo.json"
    assert json.loads(standalone.read_text())==c
