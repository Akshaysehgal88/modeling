"""Package adapter for the preserved original AMD numerical engine."""
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files

import pandas as pd

from . import _core
from .config import NOTICE, validate_config, public_facts
from .catalog import company_info
from .market_data import load_company_history


def run_model(config):
    c = deepcopy(validate_config(config))
    settings = _core.Settings(spot=c["anchor"]["price"], n_paths=c["n_paths"], seed=c["seed"], **c["settings"])
    curves = {name: {int(y): v for y, v in curve.items()} for name, curve in c["scenario_eps"].items()}
    company = company_info(c)
    multi = c["schema_version"] == 3
    history = load_company_history(c) if multi else None
    result = _core.run_model(settings, pd.DataFrame(c["events"]), prior=c["priors"],
                             scenario_eps=curves, regime_log_premiums=c["regime_log_premiums"],
                             history=history, price_levels=c.get("price_levels"))
    aliases = {"earnings_reference": "blue_earnings_reference", "reference_eps": "reference_expected_eps",
               "p50": "green_integrated_median", "p80": "orange_optimistic_p80"}
    for target, original in aliases.items():
        result["monthly"][target] = result["monthly"][original]
    result["sentiment"] = result["sentiment_log_residual"]
    result["config"] = c
    result["earnings_basis"] = (company["eps_basis"] + " scenario assumptions") if multi else "Adjusted EPS forecast assumptions (original year-by-year curves)"
    calibration_bytes = files("scenario_lab").joinpath("data/" + c["calibration"]["dataset"]).read_bytes()
    result["meta"].update(classification="model_output", notice=NOTICE,
                         engine="original_v3_preserved", anchor_classification=c["anchor"]["classification"],
                         anchor_as_of=c["anchor"]["as_of"], facts_reviewed_on=public_facts(c)["reviewed_on"],
                         company=company, native_currency=company["currency"],
                         calibration_source=("Public company-specific adjusted monthly returns and native-return peer basket" if multi else
                                             "Original user-supplied paired-return dataset; not independently source-verified"),
                         calibration_sha256=sha256(calibration_bytes).hexdigest())
    if multi:
        result["meta"]["limitations"] = f"{history['n']} complete paired monthly observations. Small-sample tails, priors, event likelihoods and future regimes are not empirically validated market probabilities."
    return result
