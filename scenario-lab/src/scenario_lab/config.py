"""Configuration for the original AMD model and monthly selector."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from importlib.resources import files
import json
import math
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from . import _core

NOTICE = ("Forecast assumptions and model outputs, not calibrated market probabilities. "
          "The original scenario inputs are retained; user-supplied inputs are not independently verified disclosures.")


def public_facts(config=None):
    if config is None:
        return json.loads(files("scenario_lab").joinpath("data/public_facts.json").read_text(encoding="utf-8"))
    from .catalog import company_facts
    return company_facts(config)


def demo_config(company_id="AMD"):
    from .catalog import company_demo
    return company_demo(company_id)


def months(config):
    return pd.period_range(config["start_month"], periods=config["horizon_months"] + 1, freq="M")


def _keys(obj, expected, label):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f"{label}: expected fields {', '.join(expected)}")


def _number(value, low, high, label, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label}: must be finite and in [{low}, {high}]")
    if integer and not isinstance(value, int):
        raise ValueError(f"{label}: must be an integer")


def _text(value, label, blank=False):
    if not isinstance(value, str) or (not blank and not value.strip()):
        raise ValueError(f"{label}: text required")


def validate_config(c):
    if not isinstance(c, dict) or type(c.get("schema_version")) is not int or c["schema_version"] not in (2, 3):
        raise ValueError("schema_version must be 2 (original AMD) or 3 (company profile)")
    multi = c["schema_version"] == 3
    fields = ["schema_version", "title", "start_month", "horizon_months", "n_paths", "seed",
              "anchor", "settings", "scenario_eps", "priors", "regime_log_premiums",
              "calibration", "events", "selector", "monthly_overrides"]
    if multi:
        fields += ["company", "sources", "forecast_notes", "price_levels"]
    _keys(c, fields, "config")
    if multi:
        _validate_company(c)
    _text(c["title"], "title")
    if c["start_month"] != "2026-10" or type(c["horizon_months"]) is not int or c["horizon_months"] != 24:
        raise ValueError("The original model uses start_month 2026-10 and horizon_months 24")
    _number(c["n_paths"], 100, 50000, "n_paths", True)
    _number(c["seed"], 0, 2**32 - 1, "seed", True)
    a = c["anchor"]
    _keys(a, ["price", "classification", "as_of", "source_url", "note"], "anchor")
    _number(a["price"], .0001 if multi else 1.001, 1e9 if multi else 19999.99, "anchor.price")
    if a["classification"] not in ("user_supplied_snapshot", "public_observation", "user_assumption", "synthetic_demo"):
        raise ValueError("Unknown anchor classification")
    _text(a["note"], "anchor.note", blank=True)
    _text(a["source_url"], "anchor.source_url", blank=True)
    try:
        observed = date.fromisoformat(a["as_of"])
    except (ValueError, TypeError) as exc:
        raise ValueError("anchor.as_of must be YYYY-MM-DD") from exc
    if a["classification"] == "public_observation":
        url = urlparse(a["source_url"])
        if url.scheme != "https" or not url.netloc:
            raise ValueError("Public anchor needs an HTTPS source_url")
        if observed > date.today() or a["as_of"][:7] != c["start_month"]:
            raise ValueError("Public anchor must be a past observation in start_month")
    limits = {"eps26": (.001, 1000), "eps27": (.001, 1000), "eps28": (.001, 1000),
              "eps29": (.001, 1000), "eps30": (.001, 1000),
              "stabilized_forward_pe": (.1, 200), "pe_normalization_months": (.1, 120),
              "initial_credit_stress": (0, 2), "initial_regime": (-2, 2),
              "credit_persistence": (.25, 1), "credit_long_run": (0, 2),
              "credit_monthly_noise": (0, 1), "credit_price_sensitivity": (0, 2),
              "evidence_strength": (0, 3), "scenario_discrimination": (0, 1),
              "earnings_scenario_spread": (0, 2), "peer_shock_scale": (0, 3),
              "idio_shock_scale": (0, 3), "optimism_feedback": (0, 3),
              "pessimism_feedback": (0, 3), "momentum_feedback": (0, 1),
              "switching_tendency": (0, 3), "sentiment_persistence": (0, .999),
              "initial_lookthrough_weight": (0, .5)}
    _keys(c["settings"], limits, "settings")
    if multi:
        for key in ("eps26", "eps27", "eps28", "eps29", "eps30"):
            limits[key] = (.000001, 1e9)
    for key, (lo, hi) in limits.items():
        _number(c["settings"][key], lo, hi, key, key == "initial_regime")
    _keys(c["scenario_eps"], _core.SCENARIO_LABELS, "scenario_eps")
    for name, curve in c["scenario_eps"].items():
        _keys(curve, [str(y) for y in range(2026, 2031)], name)
        for year, value in curve.items():
            _number(value, .000001 if multi else .001, 1e9 if multi else 1000, f"{name}.{year}")
    if not isinstance(c["priors"], list) or len(c["priors"]) != 3:
        raise ValueError("priors must contain three subjective scenario weights")
    for p in c["priors"]:
        _number(p, .000001, 1, "prior")
    if abs(sum(c["priors"]) - 1) > 1e-9:
        raise ValueError("priors must sum to one")
    if not isinstance(c["regime_log_premiums"], list) or len(c["regime_log_premiums"]) != 5:
        raise ValueError("regime_log_premiums must contain five values")
    for value in c["regime_log_premiums"]:
        _number(value, -2, 2, "regime_log_premium")
    _keys(c["calibration"], ["dataset", "window_start", "window_end", "classification"], "calibration")
    if multi:
        from .catalog import company_demo
        if c["calibration"] != company_demo(c["company"]["id"])["calibration"]:
            raise ValueError("Calibration must match the selected company's bundled history")
    elif c["calibration"] != {"dataset":"amd_peer_history.csv", "window_start":"2024-11", "window_end":"2026-09", "classification":"user_supplied_model_input"}:
        raise ValueError("Use the original bundled calibration dataset and its 23-month window")
    if not isinstance(c["events"], list) or len(c["events"]) != 24:
        raise ValueError("Exactly 24 monthly evidence rows are required")
    event_keys = ["month", "catalyst", "upside_evidence", "downside_evidence", "timing",
                  "prob_positive", "revelation_chance", "materiality", "status", "classification"]
    for event in c["events"]:
        _keys(event, event_keys, "event")
        for key in ("month", "catalyst", "upside_evidence", "downside_evidence", "timing"):
            _text(event[key], f"event.{key}")
        if event["classification"] != "forecast_assumption":
            raise ValueError("Event rows must be forecast_assumption")
        for key, high in (("prob_positive", 1), ("revelation_chance", 1), ("materiality", 3)):
            _number(event[key], 0, high, f"event.{key}")
        if event["status"] not in ("pending", "positive", "negative", "neutral"):
            raise ValueError("Invalid event status")
    if [e["month"] for e in c["events"]] != [str(m) for m in months(c)[1:]]:
        raise ValueError("Events must cover each forecast month once, in order")
    from .selector import SelectorConfig, _validated_overrides
    selector_keys = asdict(SelectorConfig())
    _keys(c["selector"], selector_keys, "selector")
    s = c["selector"]
    _number(s["selector_seed"], 0, 2**32 - 1, "selector_seed", True)
    _number(s["min_conditional_paths"], 1, c["n_paths"], "min_conditional_paths", True)
    for key, high in (("low_percentile", 1), ("high_percentile", 1), ("condition_strength", 4), ("psyche_strength", 2)):
        _number(s[key], 0, high, key)
    if s["path_index"] is not None:
        _number(s["path_index"], 0, c["n_paths"]-1, "path_index", True)
    SelectorConfig(**s).validate(c["n_paths"])
    if not isinstance(c["monthly_overrides"], list):
        raise ValueError("monthly_overrides must be a list")
    for row in c["monthly_overrides"]:
        _keys(row, ["month", "market_condition", "manual_percentile", "notes"], "monthly override")
        _text(row["month"], "override.month")
        _text(row["market_condition"], "override.market_condition")
        _text(row["notes"], "override.notes", blank=True)
        _number(row["manual_percentile"], 0, 100, "manual_percentile")
    controls = _validated_overrides(pd.DataFrame(c["monthly_overrides"]), [str(m) for m in months(c)])
    if controls.iloc[0].market_condition != "Auto" or controls.iloc[0].manual_percentile != 0:
        raise ValueError("The initial anchor cannot have a monthly override")
    for row in c["monthly_overrides"]:
        p = row["manual_percentile"] / 100
        if p and not s["low_percentile"] <= p <= s["high_percentile"]:
            raise ValueError("Forced percentiles must be inside the selector bounds")
    settings = _core.Settings(spot=a["price"], n_paths=c["n_paths"], seed=c["seed"], **c["settings"])
    settings.validate()
    curves = {name:{int(y):v for y,v in curve.items()} for name,curve in c["scenario_eps"].items()}
    for matrix in _core._eps_matrices(settings, curves):
        if not np.isfinite(matrix).all() or not (matrix > 0).all():
            raise ValueError("Scenario spread produces nonpositive or nonfinite EPS")
    return c


def load_config(path):
    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON value: {value}")
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant))


def _validate_company(c):
    from .catalog import get_company, read_data
    if not isinstance(c["company"], dict) or not isinstance(c["company"].get("id"), str):
        raise ValueError("A company profile needs a registered company identity")
    company = get_company(c["company"]["id"])
    if company["id"] == "AMD" or c["company"] != company:
        raise ValueError("Company, exchange, currency and listed unit must match the catalog")
    _keys(c["sources"], ["eps_base", "quote", "history"], "sources")
    fact = c["sources"]["eps_base"]
    baseline = read_data("companies/definitions.json")[company["id"]]["eps_base"]
    if not isinstance(fact, dict) or any(fact.get(k) != v for k, v in baseline.items()):
        raise ValueError("Disclosed EPS source must match the selected company; edit forecast settings instead")
    _number(fact.get("split_divisor_since_publication"), .000001, 1e6, "split divisor")
    _number(fact.get("aligned_value"), .000001, 1e9, "aligned EPS")
    if not math.isclose(fact["aligned_value"], fact["value"] / fact["split_divisor_since_publication"], rel_tol=1e-10):
        raise ValueError("Split-adjusted EPS does not match its disclosed base")
    quote = c["sources"]["quote"]
    history = c["sources"]["history"]
    if not isinstance(quote, dict) or quote.get("currency") != company["currency"] or quote.get("unit") != company["unit"]:
        raise ValueError("Quote currency and listed unit must match the instrument")
    peers = read_data("companies/definitions.json")[company["id"]]["peers"]
    if not isinstance(history, dict) or history.get("peer_ids") != peers:
        raise ValueError("Peer basket must belong to the selected company")
    if not isinstance(c["forecast_notes"], dict) or c["forecast_notes"].get("classification") != "forecast_assumption":
        raise ValueError("Forward company inputs must remain forecast assumptions")
    if not isinstance(c["price_levels"], list) or not c["price_levels"]:
        raise ValueError("Company profile needs native-currency price levels")
    for level in c["price_levels"]:
        _number(level, .000001, 1e10, "price level")
