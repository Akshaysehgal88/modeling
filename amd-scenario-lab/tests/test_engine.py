import numpy as np
import pytest

from amd_scenario_lab import demo_config, run_model
from amd_scenario_lab.engine import earnings_grid
from amd_scenario_lab.selector import SelectorConfig, compute_smart_selector


@pytest.fixture
def config():
    c = demo_config()
    c["n_paths"] = 500
    return c


def test_shared_anchor_ordered_quantiles_and_reproducibility(config):
    a, b = run_model(config), run_model(config)
    np.testing.assert_array_equal(a["paths"], b["paths"])
    assert np.all(a["paths"][:, 0] == config["anchor"]["price"])
    assert a["paths"].shape == (500, 25)
    assert np.isfinite(a["paths"]).all() and (a["paths"] > 0).all()
    d = a["monthly"]
    assert (np.diff(d[["p10", "p25", "p50", "p75", "p80", "p90"]], axis=1) >= 0).all()
    np.testing.assert_allclose(d.p80, np.quantile(a["paths"], .8, axis=0))
    np.testing.assert_allclose(a["beliefs"].sum(axis=2), 1)
    assert np.isin(a["states"], [-2, -1, 0, 1, 2]).all()


def test_unchanged_bearish_state_does_not_compound_a_discount(config):
    config["earnings"]["annual_growth"] = dict.fromkeys(["slowdown", "reference", "acceleration"], 0.)
    config["market"].update(initial_regime=-2, credit_persistence=1., credit_noise=0.,
                            switch_probability=0., monthly_volatility=0., terminal_pe=100/4.17)
    r = run_model(config)
    np.testing.assert_allclose(r["paths"], 100, atol=1e-10)
    np.testing.assert_allclose(r["beliefs"], np.broadcast_to(config["priors"], r["beliefs"].shape))


def test_positive_negative_evidence_moves_beliefs_in_opposite_directions(config):
    event = {"month": "2026-11", "label": "Hypothetical checkpoint", "classification": "forecast_assumption",
             "prob_positive": .5, "revelation_chance": 1., "materiality": 1., "status": "positive"}
    config["events"] = [event]
    pos = run_model(config)
    event["status"] = "negative"
    neg = run_model(config)
    assert (pos["beliefs"][:, 1, 2] > config["priors"][2]).all()
    assert (neg["beliefs"][:, 1, 2] < config["priors"][2]).all()
    assert pos["monthly"].p50.iloc[1] > neg["monthly"].p50.iloc[1]
    # Returned configuration does not change when the caller edits their input.
    assert pos["config"]["events"][0]["status"] == "positive"


def test_neutral_event_leaves_beliefs_unchanged(config):
    config["events"] = [{"month": "2026-11", "label": "Neutral what-if", "classification": "forecast_assumption",
                         "prob_positive": .5, "revelation_chance": 1., "materiality": 1., "status": "neutral"}]
    r = run_model(config)
    np.testing.assert_allclose(r["beliefs"], np.broadcast_to(config["priors"], r["beliefs"].shape))


def test_forward_eps_uses_explicit_growth_not_quarterly_annualization(config):
    grid, base = earnings_grid(config)
    assert base["period"] == "FY2025" and base["value"] == 4.17
    assert grid[0, 1] == pytest.approx(4.17 * 1.15 * (1 + .15 * 10 / 12))
    config["earnings"]["base_fact_id"] = "amd_fy2025_gaap_eps"
    _, base = earnings_grid(config)
    assert base["value"] == 2.65 and base["basis"] == "GAAP"


def test_dynamic_dates_and_horizon(config):
    config.update(start_month="2027-03", horizon_months=7)
    r = run_model(config)
    assert r["monthly"].month.tolist() == ["2027-03", "2027-04", "2027-05", "2027-06", "2027-07", "2027-08", "2027-09", "2027-10"]
    assert len(compute_smart_selector(r)) == 8


def test_selector_bounded_reproducible_and_does_not_rewrite_distribution(config):
    r = run_model(config)
    before = r["paths"].copy()
    a, b = compute_smart_selector(r), compute_smart_selector(r)
    assert a.equals(b)
    assert a.percentile.iloc[0] == 50
    assert a.percentile.between(10, 90).all()
    assert (a.selected_price >= r["monthly"].p10 - 1e-10).all()
    assert (a.selected_price <= r["monthly"].p90 + 1e-10).all()
    assert a.percentile.iloc[1:].nunique() > 5
    other = compute_smart_selector(r, SelectorConfig(seed=19))
    assert not a.equals(other)
    np.testing.assert_array_equal(r["paths"], before)


def test_path_rank_preserves_uncapped_path(config):
    r = run_model(config)
    a = compute_smart_selector(r, SelectorConfig(method="path_rank", path_index=10))
    keep = ~a.clipped.to_numpy()
    np.testing.assert_allclose(a.selected_price.to_numpy()[keep], r["paths"][10, keep])


def test_selector_ties_have_midpoint_rank(config):
    r = run_model(config)
    r["paths"][:] = 100
    a = compute_smart_selector(r)
    assert (a.percentile == 50).all()
    assert (a.selected_price == 100).all()


@pytest.mark.parametrize("cfg", [SelectorConfig(seed=-1), SelectorConfig(method="bad"), SelectorConfig(path_index=500)])
def test_invalid_selector_rejected(config, cfg):
    with pytest.raises(ValueError):
        compute_smart_selector(run_model(config), cfg)
