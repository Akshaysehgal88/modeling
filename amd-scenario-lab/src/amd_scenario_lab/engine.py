"""Joint earnings-belief, credit, regime and sentiment scenario engine.

Methods adapted from the supplied local research prototype. No historical
price series, private portfolio settings or original forecasts are bundled.
Every coefficient below is a documented illustrative modeling choice.
"""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd

from .config import NOTICE, months, public_facts, validate_config

SCENARIOS = ("slowdown", "reference", "acceleration")
REGIMES = np.arange(-2, 3)


def earnings_grid(config):
    """Calendar-year EPS projections from disclosed fiscal-year EPS.

    Treat the fiscal year as the matching calendar year (an approximation).
    Linearly blend the current/next annual EPS using month/12 as an NTM proxy.
    This is a forecast construct, not reported trailing or analyst NTM earnings.
    """
    facts = public_facts()["facts"]
    base = next(f for f in facts if f["id"] == config["earnings"]["base_fact_id"])
    start_year = int(base["period_end"][:4])
    if months(config)[0].year < start_year:
        raise ValueError("Start month predates the disclosed EPS base year")
    if months(config)[-1].year - start_year > 20:
        raise ValueError("Forecast may extend at most 20 years beyond EPS base")
    growth = np.array([config["earnings"]["annual_growth"][k] for k in SCENARIOS])
    grid = []
    for m in months(config):
        eps = base["value"] * (1 + growth) ** (m.year - start_year)
        grid.append(eps * (1 + growth * m.month / 12))
    return np.array(grid), base


def run_model(config):
    """Simulate one shared distribution; all ranks come from the same paths."""
    c = deepcopy(validate_config(config))
    eps, fact = earnings_grid(c)
    market = c["market"]
    n, h = c["n_paths"], c["horizon_months"]
    prior = np.array(c["priors"], dtype=float)
    rng = np.random.default_rng(c["seed"])
    base_eps = eps @ prior
    initial_pe = c["anchor"]["price"] / base_eps[0]
    multiples = market["terminal_pe"] + (initial_pe - market["terminal_pe"]) * np.exp(
        -np.arange(h + 1) / market["pe_normalization_months"])
    baseline = base_eps * multiples
    paths = np.full((n, h + 1), c["anchor"]["price"], dtype=float)
    states = np.full((n, h + 1), market["initial_regime"], dtype=np.int8)
    credit = np.full((n, h + 1), market["initial_credit"], dtype=float)
    beliefs = np.broadcast_to(prior, (n, h + 1, 3)).copy()
    sentiment = np.zeros((n, h + 1))
    latent = rng.choice(3, size=n, p=prior)
    events = {e["month"]: e for e in c["events"]}
    labels = [str(m) for m in months(c)]
    for t in range(1, h + 1):
        previous = beliefs[:, t - 1, :]
        posterior = previous.copy()
        positive = np.zeros(n, dtype=bool)
        published = np.zeros(n, dtype=bool)
        event = events.get(labels[t])
        materiality = event["materiality"] if event else 0
        if event:
            discrimination = market["evidence_discrimination"] * materiality
            likelihood = np.clip(event["prob_positive"] + discrimination * np.array([-1, 0, 1]), .01, .99)
            status = event["status"]
            if status == "pending":
                published = rng.random(n) < event["revelation_chance"]
                positive = rng.random(n) < likelihood[latent]
            elif status in ("positive", "negative"):
                published[:] = True
                positive[:] = status == "positive"
            likelihood_observed = np.where(positive[:, None], likelihood, 1 - likelihood)
            update = previous * likelihood_observed
            update /= update.sum(axis=1, keepdims=True)
            posterior = np.where(published[:, None], update, previous)
            if status in ("positive", "negative"):
                latent = (rng.random(n)[:, None] > np.cumsum(posterior, axis=1)).sum(axis=1).clip(0, 2)
        beliefs[:, t] = posterior
        news = np.where(published, np.where(positive, -.1, .1) * materiality, 0)
        credit[:, t] = np.clip(
            market["credit_persistence"] * credit[:, t - 1]
            + (1 - market["credit_persistence"]) * market["credit_long_run"]
            + rng.normal(0, market["credit_noise"], n) + news, 0, 2)
        signal = 2 * (posterior[:, 2] - previous[:, 2]) + (credit[:, t - 1] - credit[:, t])
        old = states[:, t - 1]
        scores = REGIMES[None, :] * signal[:, None] - .7 * np.abs(REGIMES[None, :] - old[:, None])
        scores[REGIMES[None, :] == old[:, None]] = -1000
        weights = np.exp(scores - scores.max(axis=1, keepdims=True))
        weights /= weights.sum(axis=1, keepdims=True)
        next_state = (rng.random(n)[:, None] > np.cumsum(weights, axis=1)).sum(axis=1).clip(0, 4) - 2
        states[:, t] = np.where(rng.random(n) < market["switch_probability"], next_state, old)
        residual = (market["sentiment_persistence"] * sentiment[:, t - 1]
                    + rng.normal(0, market["monthly_volatility"], n))
        sentiment[:, t] = 1.25 * np.tanh(residual / 1.25)
        expected_eps = posterior @ eps[t]
        # Anchor already reflects starting credit/regime. Only state changes
        # apply: persistent pessimism alone does not repeatedly cut the price.
        log_effect = (np.log(expected_eps / base_eps[t])
                      + market["regime_premium"] * (states[:, t] - market["initial_regime"])
                      - market["credit_sensitivity"] * (credit[:, t] - market["initial_credit"])
                      + sentiment[:, t])
        paths[:, t] = baseline[t] * np.exp(np.clip(log_effect, -3, 3))
    quantiles = np.quantile(paths, [.1, .25, .5, .75, .8, .9], axis=0)
    monthly = pd.DataFrame({"month": labels, "earnings_reference": baseline,
                            "reference_eps": base_eps, "reference_pe": multiples,
                            **{k: v for k, v in zip(("p10", "p25", "p50", "p75", "p80", "p90"), quantiles)}})
    return {"monthly": monthly, "paths": paths, "states": states,
            "credit": credit, "beliefs": beliefs, "sentiment": sentiment,
            "config": c, "eps_base_fact": fact,
            "meta": {"classification": "model_output", "notice": NOTICE,
                     "calibration": "None. Synthetic Gaussian innovations; all model parameters are illustrative forecast assumptions.",
                     "anchor_classification": c["anchor"]["classification"],
                     "anchor_as_of": c["anchor"]["as_of"],
                     "facts_reviewed_on": public_facts()["reviewed_on"]}}
