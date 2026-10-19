# Methodology and model limitations

The prototype's shared price distribution, Bayesian earnings beliefs, credit
state, five market regimes and adaptive conditional percentile idea are retained.
The implementation has been rebuilt around sourced historical EPS, configurable
dates, an explicit input contract and a synthetic demo. Original forecasts and
unsourced price/peer histories are not calibration inputs.

## Earnings and valuation reference

Let B be the selected disclosed annual diluted EPS and b its fiscal year.
For scenario s with assumed annual growth g_s:

```
EPS_s(y) = B * (1 + g_s) ** (y - b)
NTM_proxy_s(month) = EPS_s(year) * (1 + g_s * month_number / 12)
base_eps(t) = sum(prior_s * NTM_proxy_s(t))
PE_initial = anchor_price / base_eps(0)
PE(t) = terminal_PE + (PE_initial - terminal_PE) * exp(-t / normalization_months)
reference(t) = base_eps(t) * PE(t)
```

Fiscal years are approximated by matching calendar years. The month-number
blend is an annual EPS interpolation proxy, not actual trailing EPS, a full
quarterly model, a broker NTM estimate or a claim about seasonality. Both the
growth extrapolation and the P/E reference are forward assumptions. Mixing
GAAP and non-GAAP valuation conventions can invalidate comparisons.

## Joint scenarios

Each path starts at the same user-specified price, regime and credit state.
Sample a latent earnings scenario from the subjective priors. There are no
scheduled events unless the user supplies them.

For a hypothetical event, positive-evidence likelihoods across slowdown,
reference and acceleration equal `prob_positive + [-d, 0, d]`, clipped to
[0.01, 0.99], where d is discrimination times event materiality. Pending events
draw publication and outcome; forced positive/negative cases condition all
paths. Bayes' rule updates scenario weights. Forced outcomes also resample the
latent scenario from the new weights for subsequent pending evidence. Neutral
events and months without events leave the earnings weights unchanged.

Credit is a mean-reverting AR(1) process clipped to [0, 2]. Event news adds
-0.1 times materiality for positive evidence and +0.1 for negative evidence.
These numbers are illustrative method coefficients, not estimated credit spreads.

Each month can switch to another regime in {-2, -1, 0, 1, 2}. Destination scores:

```
signal = 2 * change_in_acceleration_belief + previous_credit - current_credit
score(destination) = destination * signal - 0.7 * abs(destination - old_regime)
```

The old regime is excluded when switching. Softmax scores define destination
weights; an independent switch draw uses `switch_probability`. The factors 2
and 0.7 are fixed illustrative sensitivities. Regime labels do not represent
observed future market conditions. There is no fitted macro or market process.

Sentiment follows an AR(1) state with Gaussian innovations at the assumed monthly
scale. It is softly bounded using `1.25 * tanh(residual / 1.25)`. The scale is an
innovation assumption, not a guaranteed annualized realized volatility. Prices:

```
effect = log(posterior_expected_EPS / base_eps)
       + regime_premium * (current_regime - initial_regime)
       - credit_sensitivity * (current_credit - initial_credit)
       + sentiment
price = reference * exp(clip(effect, -3, 3))
```

The 1.25 sentiment bound and +/-3 combined log-effect limits are illustrative
saturation/numerical controls; they truncate extremes and affect tails. They
are not empirically determined limits on AMD. Starting state changes are measured
relative to the anchor, preventing a repeated discount solely because a bearish
regime persists. Regimes do not themselves downgrade EPS beliefs.

## Adaptive selector

One selector seed samples a path index, or the user supplies `path_index`.
In `conditioned` mode, each month weights simulated prices by similarity to that
path's regime, credit, acceleration belief and sentiment. Match the exact regime
if at least 12 simulated paths support it; otherwise use
`exp(-1.8 * regime_distance)` for soft matching. For the three continuous states,
sum squared differences divided by `condition_bandwidth` squared and multiply
regime weights by `exp(-clip(0.5 * distance, 0, 50))`.

The weighted median's midrank in the entire monthly distribution determines the
selected percentile, clipped to [0.1, 0.9]. Price is the linear-interpolation
quantile at that clipped rank. Tied prices use their midpoint rank. All initial
prices are equal, so the first rank is 50%. Effective support is
`sum(weights)^2 / sum(weights^2)`, not an empirical confidence measure. The constants
12, 1.8, 0.5 and 50 and the P10-P90 bounds are transparent selector design choices.

In `path_rank` mode, rank the same sampled path each month instead of computing
conditional medians. Clipping can break that path's coherence. In conditioned
mode the conditions follow one simulated history; the monthly selected prices
need not follow one path. Quantile curves also need not be coherent paths.

## Scope and risks

- No price history, backtest, empirical likelihood calibration, cross-validation,
  live quote, customer-order feed or proprietary analyst estimate is used.
- Priors, Gaussian shocks, event likelihoods, transition rules and valuations are
  assumptions. P10-P90 does not establish an 80% likelihood for actual AMD prices.
- Future events can be dependent in reality. This simple latent-scenario model
  does not capture every source of dependence, crisis or structural break.
- Tail saturation and simplified EPS growth can materially distort outcomes.
- This is an EPS/valuation research simulator, not a three-statement financial
  model. It does not model a balance sheet, cash flows, dilution or tax lots.
- No personal holdings, sale target, currency conversion or tax planning enters
  the package. This tool is for scenario exploration, not investment instructions.
- Reproducibility assumes identical configuration and dependency versions;
  cross-version random-number and floating-point behavior can differ.
