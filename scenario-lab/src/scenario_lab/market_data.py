"""Calibrate the original bootstrap mechanism on the selected company's data."""
from importlib.resources import files

import numpy as np
import pandas as pd


def load_company_history(config):
    source = config["calibration"]
    path = files("scenario_lab").joinpath("data/" + source["dataset"])
    with path.open("r", encoding="utf-8") as f:
        frame = pd.read_csv(f, dtype={"month": str})
    if set(frame) != {"month", "asset_return", "peer_return"}:
        raise ValueError("Company history needs month, asset_return and peer_return")
    frame = frame.loc[frame.month.between(source["window_start"], source["window_end"])].copy()
    if len(frame) < 12 or frame.month.duplicated().any() or not frame.month.is_monotonic_increasing:
        raise ValueError("Company calibration needs at least 12 ordered unique monthly pairs")
    expected = pd.period_range(source["window_start"], source["window_end"], freq="M").astype(str).tolist()
    if frame.month.tolist() != expected:
        raise ValueError("Company history has gaps or does not cover its stated window")
    values = frame[["asset_return", "peer_return"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Returns must be finite and greater than -100%")
    a = np.log1p(values[:, 0])
    p = np.log1p(values[:, 1])
    variance = np.var(p, ddof=1)
    if variance < 1e-12:
        raise ValueError("Peer-return variance is too small for calibration")
    beta = float(np.cov(p, a, ddof=1)[0, 1] / variance)
    residual = a - (np.mean(a) - beta * np.mean(p)) - beta * p
    return {"peer": p - p.mean(), "idio": residual - residual.mean(), "beta": beta, "n": len(p),
            "peer_std": float(np.std(p, ddof=1)), "idio_std": float(np.std(residual, ddof=1)),
            "asset_std": float(np.std(a, ddof=1))}
