"""Conditioned percentile overlay adapted from the supplied research prototype.

The sampled conditioning history is hypothetical. Conditional medians are
computed independently per month and need not be a coherent price trajectory.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

LABELS = {-2: "Severe panic", -1: "Risk-off", 0: "Neutral", 1: "Optimistic", 2: "Euphoric"}


@dataclass
class SelectorConfig:
    seed: int = 7
    method: str = "conditioned"
    path_index: int | None = None

    def validate(self, n):
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or not 0 <= self.seed < 2**32:
            raise ValueError("Selector seed must be a nonnegative 32-bit integer")
        if self.method not in ("conditioned", "path_rank"):
            raise ValueError("Selector method must be conditioned or path_rank")
        if self.path_index is not None and (isinstance(self.path_index, bool) or not isinstance(self.path_index, int) or not 0 <= self.path_index < n):
            raise ValueError("Selector path_index out of range")


def compute_smart_selector(result, config=None):
    """Select within P10-P90; expose raw price, rank and effective support.

    Condition on regime plus current credit, acceleration belief and sentiment.
    If fewer than 12 paths share the regime, soften matching by regime distance.
    No actual future states or future data are used.
    """
    cfg = config or SelectorConfig(**result["config"]["selector"])
    prices = result["paths"]
    n, points = prices.shape
    cfg.validate(n)
    idx = cfg.path_index if cfg.path_index is not None else int(np.random.default_rng(cfg.seed).integers(n))
    bandwidth = result["config"]["market"]["condition_bandwidth"]
    selected = []
    for t in range(points):
        ordered = np.sort(prices[:, t])
        state = int(result["states"][idx, t])
        same = result["states"][:, t] == state
        count = int(same.sum())
        softened = count < 12
        effective = float(n)
        if t == 0 or cfg.method == "path_rank":
            raw = float(prices[idx, t])
        else:
            state_weights = np.exp(-1.8 * np.abs(result["states"][:, t] - state)) if softened else same.astype(float)
            distance = np.zeros(n)
            for values in (result["credit"][:, t], result["beliefs"][:, t, 2], result["sentiment"][:, t]):
                distance += ((values - values[idx]) / bandwidth)**2
            w = state_weights * np.exp(-np.clip(.5 * distance, 0, 50))
            order = np.argsort(prices[:, t])
            median_index = min(n - 1, int(np.searchsorted(np.cumsum(w[order]), w.sum() / 2)))
            raw = float(prices[order[median_index], t])
            effective = float(w.sum()**2 / np.sum(w**2))
        left, right = np.searchsorted(ordered, raw, side="left"), np.searchsorted(ordered, raw, side="right")
        rank = .5 if left == 0 and right == n else float((left + right - 1) / (2 * (n - 1)))
        bounded = float(np.clip(rank, .1, .9))
        price = float(np.quantile(ordered, bounded))
        selected.append({"month": result["monthly"].month.iloc[t], "selected_price": price,
                         "percentile": bounded * 100, "raw_percentile": rank * 100,
                         "raw_price": raw, "clipped": abs(bounded - rank) > 1e-10,
                         "path_index": idx, "market_regime": LABELS[state],
                         "credit_stress": float(result["credit"][idx, t]),
                         "acceleration_belief": float(result["beliefs"][idx, t, 2]),
                         "sentiment": float(result["sentiment"][idx, t]),
                         "same_regime_count": count, "effective_sample_size": effective,
                         "softened_regime_matching": softened, "method": cfg.method})
    return pd.DataFrame(selected)
