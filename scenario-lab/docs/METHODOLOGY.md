# Simulation methodology

Scenario Lab uses one shared engine for all 20 company presets. A selected
company supplies its own starting price, earnings cases, historical returns,
business-event assumptions, and listing currency. The engine combines these
inputs with funding conditions, market mood, and price variation to produce a
monthly distribution of scenarios.

The monthly selector chooses values from that distribution for the magenta
line. It does not change the simulated paths. Currency conversion applies only
to the displayed and exported amounts.

## Paired-return calibration

Use the selected company's paired asset and peer returns over its recorded
calibration window. Convert simple returns to logarithms using `log1p`. Estimate:

```
beta = sample_covariance(peer_log_return, asset_log_return) / sample_variance(peer_log_return)
residual = asset_log_return - (mean(asset_log_return) - beta * mean(peer_log_return))
           - beta * peer_log_return
```

Demean peer returns and residuals. Each simulation month bootstraps from those
two arrays, scaled separately by `peer_shock_scale` and `idio_shock_scale`.
Each dataset records its source basis and observation count. Supplied model
inputs are distinguished from provider-sourced observations. Return draws use
the recorded samples; funding-stress innovations use Gaussian noise. See
[Company inputs and sources](COMPANY_DATA.md) for data coverage and exceptions.

## Earnings scenarios and reference

For each year, the reference EPS is the editable FY2026-FY2030 setting. Scenario
templates define the relative slowdown/acceleration differences:

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

Starting case weights come from the selected preset and are editable. For pathwise
pricing, farther-ahead look-through equals the starting weight plus 0.068 times
positive regime change plus 0.10 times the change in acceleration belief, clipped
to [0.03, 0.62]. The reference uses unchanged initial weights. These coefficients
are shared modeling assumptions.

## Evidence and credit

For each month's event row, relevance is materiality times evidence
strength. Likelihood separation is discrimination times `min(relevance, 1.6)`,
clipped to [0, 0.35]. Positive-evidence likelihoods are the row's base probability
minus that separation, unchanged, and plus that separation, clipped to
[0.035, 0.965] across the three scenarios.

Draw one latent scenario per path from the priors. Pending events draw evidence
arrival and outcome conditional on that latent scenario. Forced positive/negative
outcomes condition every path and resample the latent case from the updated
posterior for subsequent evidence. Neutral means no evidence. Bayes' rule updates
scenario weights; remaining in a bearish regime alone does not downgrade EPS.

Credit stress follows a mean-reverting process, plus Gaussian noise
and evidence news of -0.11 for positive or +0.12 for negative evidence times
`min(relevance, 1.5)`. Credit is clipped to [0, 2]. Event descriptions,
including timing assertions, are scenario inputs, not independently verified facts.

## Regime hazards, sentiment and feedback

The switching signal combines:

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
in extreme regimes. Sentiment persistence and bounded momentum feedback carry
price effects between months. Feedback uses optimism/pessimism strengths (0.65 in neutral),
`tanh(momentum * 3) * 0.06`, scaled by `momentum_feedback`. Sentiment uses
`1.25 * tanh(residual / 1.25)` saturation. Updated momentum is
`clip(0.65 * old_momentum + 0.35 * log_return, -0.5, 0.5)`.

Price equals the reference times the exponential of posterior-EPS, regime,
credit-change and sentiment effects, clipped jointly to [-2.4, 2.4]. Regime log
premiums come from the selected scenario configuration. Regime and credit effects
are measured relative to the common starting state. An unchanged bearish state
does not impose a new bearish discount every month.

## Adaptive selection and monthly controls

One selector seed chooses a hypothetical market/evidence path. In `conditioned`
mode, weight prices with the same contemporaneous regime by credit distance
(bandwidth 0.40), acceleration-belief distance (0.23), and sentiment distance
(0.38), scaled by the configured matching strengths. Weight penalties are
`0.5 * condition_strength * (credit_distance + belief_distance + psyche_strength * sentiment_distance)`,
clipped to [0, 50] before exponentiation.

Automatic rare regimes with fewer than the configured minimum number of paths
(12 by default) soften regime matching using `exp(-1.8 * regime_distance)`. Explicitly requested regimes with too few
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

Randomness is seeded and reproducible. The model does not add smoothing or
assign market turning points to particular calendar months.

The short calibration samples do not reliably estimate tails or credit crises.
Starting case weights, evidence likelihoods, regime transitions, future EPS,
funding dynamics, and feedback strengths are assumptions rather than fitted
market probabilities. Percentile bands are within-model ranks, not calibrated
confidence intervals. Conditional monthly medians need not form one continuous
simulated price path. Manually selected conditions and future event outcomes
are what-if assumptions.

The shared date grid runs from October 2026 to October 2028. Rebasing requires
updating earnings and market data together. There is no live market-data feed.
Reproduction assumes consistent dependency versions and floating-point behavior;
audit exports record Python, NumPy, and pandas versions.

## Company inputs and currency

Each preset supplies instrument metadata, annual EPS curves, starting
conditions, event assumptions, native-unit price levels, and a calibrated
return sample to the shared engine. Selecting a company does not change the
formulas, random-draw sequence, or monthly selection rules.

The loader checks complete monthly coverage and uses the same covariance-beta
and residual formulas across companies. Input bounds accommodate each listing's
price and EPS scale. Values remain in the native currency during simulation.
Display conversion leaves returns, P/E ratios, case weights, percentile choices,
and random draws unchanged.

Company workspaces isolate edits and restore each company's saved session when
switching back. See [Company inputs and sources](COMPANY_DATA.md) for listing,
fiscal-calendar, price-adjustment, and EPS-basis conventions.

## Numerical regression checks

Tests compare the baseline monthly results and selector outputs with the
bundled reference fixtures. Separate checks cover company-specific inputs,
currency presentation, and monthly controls. These checks verify consistency
of calculations; they do not validate the forecasts as market predictions.
