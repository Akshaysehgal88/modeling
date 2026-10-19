from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scenario_lab import demo_config, run_model, compute_smart_selector, SelectorConfig
from scenario_lab.report import output_table


@pytest.fixture
def config():
    c = demo_config()
    c["n_paths"] = 600
    return c


def test_default_results_match_both_original_supplied_outputs():
    result = run_model(demo_config())
    selected = compute_smart_selector(result)
    fixture = Path(__file__).with_name("fixtures")
    for name, actual in (("original_monthly.csv", output_table(result, selected)), ("original_selector.csv", selected)):
        expected = pd.read_csv(fixture / name)
        for column in expected:
            assert column in actual
            if pd.api.types.is_numeric_dtype(expected[column]):
                np.testing.assert_allclose(actual[column], expected[column], rtol=0, atol=1e-8, err_msg=column)
            elif column != "selector_source":
                assert actual[column].equals(expected[column]), column
    assert result["meta"]["calibration"]["n"] == 23
    assert selected.selector_path_index.iloc[0] == 2053


def test_same_seed_preserves_paths_anchor_and_quantiles(config):
    a, b = run_model(config), run_model(config)
    np.testing.assert_array_equal(a["paths"], b["paths"])
    assert np.all(a["paths"][:, 0] == config["anchor"]["price"])
    assert (a["paths"] > 0).all() and np.isfinite(a["paths"]).all()
    q = a["monthly"][["p10", "p25", "p50", "p75", "p80", "p90"]]
    assert (np.diff(q, axis=1) >= 0).all()
    np.testing.assert_allclose(a["monthly"].p80, np.quantile(a["paths"], .8, axis=0), atol=.005)
    np.testing.assert_allclose(a["beliefs"].sum(axis=2), 1)
    assert set(a["touches"]) == {"500", "600", "700", "800", "900", "1000", "1200"}


def test_unchanged_bearish_state_does_not_compound_discount(config):
    for key in ("eps26", "eps27", "eps28", "eps29", "eps30"):
        config["settings"][key] = 20.
    config["settings"].update(initial_regime=-2, earnings_scenario_spread=0., switching_tendency=0.,
        credit_persistence=1., credit_monthly_noise=0., peer_shock_scale=0., idio_shock_scale=0.,
        momentum_feedback=0., stabilized_forward_pe=config["anchor"]["price"] / 20)
    for event in config["events"]:
        event["status"] = "neutral"
    r = run_model(config)
    np.testing.assert_allclose(r["paths"], config["anchor"]["price"], atol=1e-8)
    np.testing.assert_allclose(r["beliefs"], np.broadcast_to(config["priors"], r["beliefs"].shape))


def test_evidence_updates_earnings_beliefs(config):
    for event in config["events"]:
        event["status"] = "neutral"
    positive, negative = deepcopy(config), deepcopy(config)
    positive["events"][0]["status"] = "positive"
    negative["events"][0]["status"] = "negative"
    p, n = run_model(positive), run_model(negative)
    assert (p["beliefs"][:, 1, 2] > config["priors"][2]).all()
    assert (n["beliefs"][:, 1, 2] < config["priors"][2]).all()
    assert p["monthly"].p50.iloc[1] > n["monthly"].p50.iloc[1]


def test_selector_reproducible_and_inside_original_envelope(config):
    r = run_model(config)
    a, b = compute_smart_selector(r), compute_smart_selector(r)
    assert a.equals(b)
    assert a.smart_percentile.between(10, 90).all()
    assert (a.selected_price >= r["monthly"].p10 - .011).all()
    assert (a.selected_price <= r["monthly"].p90 + .011).all()
    assert a.smart_percentile.iloc[1:].nunique() > 5
    assert not a.equals(compute_smart_selector(r, SelectorConfig(selector_seed=8)))


def test_monthly_percentile_override_changes_only_selected_month(config):
    r = run_model(config)
    before = r["paths"].copy()
    automatic = compute_smart_selector(r)
    overrides = deepcopy(config["monthly_overrides"])
    overrides[7]["manual_percentile"] = 80.
    chosen = compute_smart_selector(r, overrides=overrides)
    assert chosen.smart_percentile.iloc[7] == 80
    assert chosen.selected_price.iloc[7] == pytest.approx(r["monthly"].p80.iloc[7], abs=.01)
    # A changed price also changes the following month's return diagnostic.
    exclude = ["selected_monthly_return_percent"]
    assert automatic.drop(columns=exclude, index=7).equals(chosen.drop(columns=exclude, index=7))
    np.testing.assert_array_equal(r["paths"], before)


def test_monthly_regime_override_and_rare_regime_rejection(config):
    r = run_model(config)
    month = 12
    regime = int(np.bincount(r["states"][:, month] + 2).argmax() - 2)
    labels = {-2:"Severe panic", -1:"Risk-off", 0:"Neutral", 1:"Optimistic", 2:"Euphoric"}
    overrides = deepcopy(config["monthly_overrides"])
    overrides[month]["market_condition"] = labels[regime]
    selected = compute_smart_selector(r, overrides=overrides)
    assert selected.market_type.iloc[month] == labels[regime]
    assert selected.selector_source.iloc[month].startswith("Conditional price given manually")
    r["states"][:, month] = -1
    overrides[month]["market_condition"] = "Euphoric"
    with pytest.raises(ValueError, match="only 0 model paths"):
        compute_smart_selector(r, overrides=overrides)


def test_path_rank_preserves_uncapped_original_trajectory(config):
    r = run_model(config)
    selected = compute_smart_selector(r, SelectorConfig(method="path_rank", path_index=10))
    keep = ~selected.capped_to_p10_p90.to_numpy()
    np.testing.assert_allclose(selected.selected_price.to_numpy()[keep], r["paths"][10, keep], atol=.005)


def test_saved_monthly_choices_round_trip_without_changing_distribution(config):
    base = run_model(config)
    changed = deepcopy(config)
    changed["monthly_overrides"][5]["manual_percentile"] = 75.
    result = run_model(changed)
    np.testing.assert_array_equal(result["paths"], base["paths"])
    assert compute_smart_selector(result).smart_percentile.iloc[5] == 75
    changed["events"][0]["status"] = "negative"
    assert result["config"]["events"][0]["status"] == "pending"
