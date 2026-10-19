# Preserved original methodology

The model is the supplied AMD v3 numerical engine. Packaging adapters expose its
inputs and add provenance/export fields; they do not replace the equations or
random sampling. The original personal-finance settings and proceeds/target
calculations are removed. The original selector and chart routines are retained.

## Default reproduction

The default scenario includes the original 6,000 paths, model seed 20261018,
selector seed 20261019, $528.75 anchor, 24 evidence rows, forward EPS assumptions
and paired-return dataset. Tests compare every numeric column of the original
monthly comparison and selector CSVs against restored results. The default
selected conditioning path remains index 2053. Original rounding is retained.

## Paired-return calibration

Filter the original history to November 2024-September 2026 (23 observations).
Convert peer and AMD simple returns to logarithms using `log1p`. Estimate:

```
beta = sample_covariance(peer_log_return, AMD_log_return) / sample_variance(peer_log_return)
residual = AMD_log_return - (mean(AMD_log_return) - beta * mean(peer_log_return))
           - beta * peer_log_return
```

Demean peer returns and residuals. Each simulation month bootstraps from those
two arrays, scaled separately by `peer_shock_scale` and `idio_shock_scale`.
The original data are user-supplied model inputs, not independently verified
market observations in this package. No synthetic Gaussian process is substituted
for these return draws. Credit innovations remain Gaussian as in the original.

## Earnings scenarios and reference

For each year, the reference EPS is the editable FY2026-FY2030 setting. Scenario
templates preserve the original relative slowdown/acceleration distances:

```
scenario_EPS(year) = edited_reference_EPS(year) *
    (1 + earnings_scenario_spread * (template_scenario(year) / template_reference(year) - 1))
NTM(month, ahead) = (1 - month_number / 12) * EPS(year + ahead)
                   + month_number / 12 * EPS(year + ahead + 1)
```

Blend NTM and the following year's NTM using `initial_lookthrough_weight`, then
average across the subjective priors to form reference earnings. Initial P/E
anchors the reference to the starting price. P/E exponentially normalizes to
`stabilized_forward_pe` over `pe_normalization_months`. This is an assumed
valuation reference, not disclosed forward earnings, fair value or consensus.

Initial priors are 25% slowdown, 55% reference and 20% acceleration. For pathwise
pricing, farther-ahead look-through equals the starting weight plus 0.068 times
positive regime change plus 0.10 times the change in acceleration belief, clipped
to [0.03, 0.62]. The reference uses unchanged initial weights. These coefficients
are the original modeling assumptions.

## Evidence and credit

For each month's original event row, relevance is materiality times evidence
strength. Likelihood separation is discrimination times `min(relevance, 1.6)`,
clipped to [0, 0.35]. Positive-evidence likelihoods are the row's base probability
minus that separation, unchanged, and plus that separation, clipped to
[0.035, 0.965] across the three scenarios.

Draw one latent scenario per path from the priors. Pending events draw evidence
arrival and outcome conditional on that latent scenario. Forced positive/negative
outcomes condition every path and resample the latent case from the updated
posterior for subsequent evidence. Neutral means no evidence. Bayes' rule updates
scenario weights; remaining in a bearish regime alone does not downgrade EPS.

Credit stress follows its original mean-reverting process, plus Gaussian noise
and evidence news of -0.11 for positive or +0.12 for negative evidence times
`min(relevance, 1.5)`. Credit is clipped to [0, 2]. Original event descriptions,
including timing assertions, are scenario inputs, not independently verified facts.

## Regime hazards, sentiment and feedback

The switching signal is the original combination:

```
2.2 * change_in_acceleration_belief
+ 1.9 * (previous_credit - current_credit)
+ 2.0 * peer_shock
+ 0.8 * clip(momentum, -0.35, 0.35)
- 0.50 * (current_credit - 0.70)
```

Switching hazard equals 0.075 + 0.065 times capped regime duration / 12,
plus 0.12 times absolute belief change, plus 0.11 times absolute credit change.
Scale by switching tendency and clip to [0, 0.85]. Destination softmax scores
are `regime * signal * 1.5 - 0.7 * distance - 0.12 * abs(regime)`, excluding
the current regime. Softmax exponent differences are clipped to [-40, 0].

Return innovation is `beta * peer_shock + idiosyncratic_shock`, amplified by 1.22
in extreme regimes. Sentiment persistence and bounded momentum feedback are
unchanged. Feedback uses optimism/pessimism strengths (0.65 in neutral),
`tanh(momentum * 3) * 0.06`, scaled by `momentum_feedback`. Sentiment uses
`1.25 * tanh(residual / 1.25)` saturation. Updated momentum is
`clip(0.65 * old_momentum + 0.35 * log_return, -0.5, 0.5)`.

Price equals the reference times the exponential of posterior-EPS, regime,
credit-change and sentiment effects, clipped jointly to [-2.4, 2.4]. The original
regime log premiums are [-0.18, -0.09, 0, 0.10, 0.24]. Regime and credit effects
are measured relative to the common starting state. An unchanged bearish state
does not impose a new bearish discount every month.

## Adaptive selection and monthly controls

One selector seed chooses a hypothetical market/evidence path. In `conditioned`
mode, weight prices with the same contemporaneous regime by credit distance
(bandwidth 0.40), acceleration-belief distance (0.23), and sentiment distance
(0.38), with the original condition and psyche strengths. Weight penalties are
`0.5 * condition_strength * (credit_distance + belief_distance + psyche_strength * sentiment_distance)`,
clipped to [0, 50] before exponentiation.

Automatic rare regimes with fewer than 12 matching paths soften regime matching
using `exp(-1.8 * regime_distance)`. Explicitly requested regimes with too few
paths raise an error. Effective support is `sum(weights)^2 / sum(weights^2)`;
it is a simulation diagnostic, not empirical confidence.

Rank the weighted median in the entire month's price distribution using a
midrank for ties. Clip rank to the configured percentile bounds (P10-P90 by
default), and select the corresponding linear quantile. The initial anchor
stays fixed. In `path_rank` mode, use one exact path's rank instead of the
conditional median; clipping can alter that path.

Per-month manual percentiles take precedence over manual regimes. Monthly
overrides never modify simulated paths, beliefs or regime transitions; they
select from the shared distribution. Overriding one price also changes its and
the next month's return diagnostic, without changing other selected prices.
JSON and CSV exports preserve the exact controls used.

## Interpretation and limitations

The original model remains stochastic. Its randomness is seeded and reproducible;
there is no added postprocessing to make the curve look sharper or to force
calendar turning points. The restoration preserves model behavior rather than
optimizing the appearance of results.

The 23-month sample does not reliably estimate tails or credit crises. Priors,
likelihoods, hazards, future EPS, credit dynamics and feedback strengths are
hypotheses rather than fitted market probabilities. Quantile bands are
within-model ranks, not calibrated confidence intervals. Conditional monthly
medians need not be a coherent price path. Neither a manually selected regime
nor a future event outcome is known in advance.

The date grid is intentionally the original October 2026-October 2028 snapshot.
Rebasing it requires updating the earnings and data together. The tool has no live
market-data feed, full three-statement financial model or personal tax/portfolio
planning module. Reproduction assumes consistent dependency versions and
floating-point behavior; audit exports record Python, NumPy and pandas versions.
