import json
from pathlib import Path

import pytest

from amd_scenario_lab.config import demo_config, load_config, public_facts, validate_config


@pytest.mark.parametrize("path,value", [
    (("n_paths",), 0), (("n_paths",), True), (("seed",), -1),
    (("horizon_months",), 0), (("start_month",), "2026-13"),
    (("anchor", "price"), float("nan")), (("anchor", "price"), float("inf")),
    (("market", "monthly_volatility"), -.1), (("market", "initial_regime"), .5),
    (("market", "credit_persistence"), 1.1), (("priors",), [.1, .1, .1]),
    (("earnings", "classification"), "public_disclosed_fact"),
    (("earnings", "base_fact_id"), "amd_q22026_nongaap_eps"),
    (("selector", "path_index"), 3000), (("anchor", "as_of"), "bad"),
])
def test_invalid_inputs(path, value):
    c = demo_config()
    parent = c
    for p in path[:-1]:
        parent = parent[p]
    parent[path[-1]] = value
    with pytest.raises(ValueError):
        validate_config(c)


def test_unknown_fields_rejected():
    c = demo_config()
    c["unrecognized"] = 1
    with pytest.raises(ValueError, match="expected fields"):
        validate_config(c)


def test_public_anchor_requires_source_and_matching_month():
    c = demo_config()
    c["anchor"]["classification"] = "public_observation"
    with pytest.raises(ValueError, match="source_url"):
        validate_config(c)
    c["anchor"]["source_url"] = "https://example.com/disclosure"
    c["anchor"]["as_of"] = "2025-01-01"
    with pytest.raises(ValueError, match="start_month"):
        validate_config(c)


def test_duplicate_and_out_of_horizon_events_rejected():
    c = demo_config()
    event = {"month": "2026-11", "label": "Hypothetical", "classification": "forecast_assumption",
             "prob_positive": .5, "revelation_chance": .5, "materiality": .5, "status": "pending"}
    c["events"] = [event, event.copy()]
    with pytest.raises(ValueError, match="unique months"):
        validate_config(c)
    c["events"] = [dict(event, month="2035-01")]
    with pytest.raises(ValueError, match="horizon"):
        validate_config(c)


def test_json_nonfinite_rejected(tmp_path):
    p = tmp_path / "scenario.json"
    c = demo_config()
    c["anchor"]["price"] = float("nan")
    p.write_text(json.dumps(c), encoding="utf-8")
    with pytest.raises(ValueError, match="Nonfinite"):
        load_config(p)


def test_bundled_fact_register_has_primary_provenance():
    facts = public_facts()["facts"]
    assert len({f["id"] for f in facts}) == len(facts)
    for f in facts:
        assert f["classification"] == "public_disclosed_fact"
        assert f["source_url"].startswith("https://ir.amd.com/")
        assert f["source_location"] and f["published_on"] and f["period_end"]
        assert f["basis"] in ("GAAP", "non-GAAP")
    # Protect the publication allowlist against accidental additions of datasets.
    data = Path(__file__).parents[1] / "src" / "amd_scenario_lab" / "data"
    assert {p.name for p in data.iterdir() if p.is_file()} == {"demo.json", "public_facts.json"}
