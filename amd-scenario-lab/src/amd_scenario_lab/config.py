"""Strict input contract: facts and forecasts have separate provenance."""
from __future__ import annotations

import json
import math
import re
from datetime import date
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

NOTICE = ("Illustrative forecast scenario, not a market prediction. Percentiles are "
          "within-model ranks, not calibrated probabilities or confidence intervals.")


def public_facts():
    return json.loads(files("amd_scenario_lab").joinpath("data/public_facts.json").read_text(encoding="utf-8"))


def demo_config():
    return json.loads(files("amd_scenario_lab").joinpath("data/demo.json").read_text(encoding="utf-8"))


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


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: nonempty text required")


def validate_config(c):
    """Reject unknown fields, malformed dates, nonfinite values and missing provenance.

    Source URLs are provenance assertions, not automated verification of a fact.
    Only the shipped fact register has been manually checked against its sources.
    """
    _keys(c, ["schema_version", "title", "start_month", "horizon_months", "n_paths",
              "seed", "anchor", "earnings", "priors", "market", "events", "selector"], "config")
    if type(c["schema_version"]) is not int or c["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    _text(c["title"], "title")
    if not isinstance(c["start_month"], str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", c["start_month"]):
        raise ValueError("start_month must be YYYY-MM")
    _number(c["horizon_months"], 1, 60, "horizon_months", True)
    _number(c["n_paths"], 100, 20000, "n_paths", True)
    _number(c["seed"], 0, 2**32 - 1, "seed", True)
    if c["n_paths"] * (c["horizon_months"] + 1) > 650000:
        raise ValueError("Reduce paths or horizon: maximum 650,000 path-months")
    a = c["anchor"]
    _keys(a, ["price", "classification", "as_of", "source_url", "note"], "anchor")
    _number(a["price"], .01, 100000, "anchor.price")
    if a["classification"] not in ("synthetic_demo", "public_observation", "user_assumption"):
        raise ValueError("Unknown anchor classification")
    _text(a["note"], "anchor.note")
    if not isinstance(a["source_url"], str):
        raise ValueError("anchor.source_url must be text")
    try:
        observed = date.fromisoformat(a["as_of"])
    except (TypeError, ValueError) as exc:
        raise ValueError("anchor.as_of must be YYYY-MM-DD") from exc
    if a["classification"] == "public_observation":
        u = urlparse(a["source_url"])
        if u.scheme != "https" or not u.netloc:
            raise ValueError("Public anchor needs an HTTPS source_url")
        if observed > date.today() or a["as_of"][:7] != c["start_month"]:
            raise ValueError("Public anchor must be a past observation in start_month")
    e = c["earnings"]
    _keys(e, ["base_fact_id", "annual_growth", "classification", "note"], "earnings")
    if e["classification"] != "forecast_assumption":
        raise ValueError("Future earnings must be labeled forecast_assumption")
    _text(e["note"], "earnings.note")
    if e["base_fact_id"] not in {f["id"] for f in public_facts()["facts"] if f["metric"] == "diluted_eps" and f["period_type"] == "annual"}:
        raise ValueError("base_fact_id must identify bundled annual disclosed EPS")
    scenario_names = ["slowdown", "reference", "acceleration"]
    _keys(e["annual_growth"], scenario_names, "annual_growth")
    for name, v in e["annual_growth"].items():
        _number(v, -.8, 2, f"annual_growth.{name}")
    if not e["annual_growth"]["slowdown"] <= e["annual_growth"]["reference"] <= e["annual_growth"]["acceleration"]:
        raise ValueError("Growth rates must be ordered slowdown <= reference <= acceleration")
    if not isinstance(c["priors"], list) or len(c["priors"]) != 3:
        raise ValueError("priors must be three subjective scenario weights")
    for p in c["priors"]:
        _number(p, .0001, 1, "prior")
    if abs(sum(c["priors"]) - 1) > 1e-9:
        raise ValueError("priors must sum to one")
    limits = {"terminal_pe": (.1, 200), "pe_normalization_months": (1, 120),
              "initial_regime": (-2, 2), "initial_credit": (0, 2),
              "credit_long_run": (0, 2), "credit_persistence": (0, 1),
              "credit_noise": (0, 1), "credit_sensitivity": (0, 2),
              "monthly_volatility": (0, 1), "sentiment_persistence": (0, .99),
              "switch_probability": (0, 1), "regime_premium": (0, .5),
              "evidence_discrimination": (0, .4), "condition_bandwidth": (.05, 2)}
    _keys(c["market"], limits, "market")
    for key, (lo, hi) in limits.items():
        _number(c["market"][key], lo, hi, key, key == "initial_regime")
    if not isinstance(c["events"], list):
        raise ValueError("events must be a list")
    future_months = {str(m) for m in months(c)[1:]}
    seen = set()
    for event in c["events"]:
        _keys(event, ["month", "label", "classification", "prob_positive", "revelation_chance", "materiality", "status"], "event")
        if event["month"] not in future_months or event["month"] in seen:
            raise ValueError("Events need unique months inside the forecast horizon")
        seen.add(event["month"])
        _text(event["label"], "event.label")
        if event["classification"] != "forecast_assumption":
            raise ValueError("Event timing and outcomes must be forecast_assumption")
        if event["status"] not in ("pending", "positive", "negative", "neutral"):
            raise ValueError("Invalid hypothetical event status")
        for key in ("prob_positive", "revelation_chance", "materiality"):
            _number(event[key], 0, 1, f"event.{key}")
    _keys(c["selector"], ["seed", "method", "path_index"], "selector")
    _number(c["selector"]["seed"], 0, 2**32 - 1, "selector.seed", True)
    if c["selector"]["method"] not in ("conditioned", "path_rank"):
        raise ValueError("selector.method must be conditioned or path_rank")
    if c["selector"]["path_index"] is not None:
        _number(c["selector"]["path_index"], 0, c["n_paths"] - 1, "selector.path_index", True)
    return c


def load_config(path):
    def reject_constant(s):
        raise ValueError(f"Nonfinite JSON value: {s}")
    c = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)
    return validate_config(c)
