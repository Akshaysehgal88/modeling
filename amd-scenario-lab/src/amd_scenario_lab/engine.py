"""Package adapter for the preserved original AMD numerical engine."""
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files

import pandas as pd

from . import _core
from .config import NOTICE, validate_config, public_facts


def run_model(config):
    c = deepcopy(validate_config(config))
    settings = _core.Settings(spot=c["anchor"]["price"], n_paths=c["n_paths"], seed=c["seed"], **c["settings"])
    curves = {name: {int(y): v for y, v in curve.items()} for name, curve in c["scenario_eps"].items()}
    result = _core.run_model(settings, pd.DataFrame(c["events"]), prior=c["priors"],
                             scenario_eps=curves, regime_log_premiums=c["regime_log_premiums"])
    aliases = {"earnings_reference": "blue_earnings_reference", "reference_eps": "reference_expected_eps",
               "p50": "green_integrated_median", "p80": "orange_optimistic_p80"}
    for target, original in aliases.items():
        result["monthly"][target] = result["monthly"][original]
    result["sentiment"] = result["sentiment_log_residual"]
    result["config"] = c
    result["earnings_basis"] = "Adjusted EPS forecast assumptions (original year-by-year curves)"
    calibration_bytes = files("amd_scenario_lab").joinpath("data/amd_peer_history.csv").read_bytes()
    result["meta"].update(classification="model_output", notice=NOTICE,
                         engine="original_v3_preserved", anchor_classification=c["anchor"]["classification"],
                         anchor_as_of=c["anchor"]["as_of"], facts_reviewed_on=public_facts()["reviewed_on"],
                         calibration_source="Original user-supplied paired-return dataset; not independently source-verified",
                         calibration_sha256=sha256(calibration_bytes).hexdigest())
    return result
