# Input and publication policy

Scenario Lab separates disclosed historical figures, dated market observations,
editable forecast assumptions, and simulated results. Each company preset uses
the same classification rules. Source records and preset-specific exceptions
are documented in [Sources and input records](SOURCES.md) and
[Company inputs and sources](COMPANY_DATA.md).

## Classifications

| Classification | Meaning |
| --- | --- |
| `public_disclosed_fact` | Historical issuer figure with a reviewed public source |
| `public_market_data` | Provider-sourced price, return, or exchange-rate observation |
| `public_observation` | Dated starting price with an HTTPS source; custom entries are not independently verified |
| `user_supplied_snapshot` | Supplied starting price, not independently source-verified by the package |
| `user_supplied_model_input` | Supplied calibration series, not independently source-verified by the package |
| `forecast_assumption` | Earnings curve, event window, likelihood, outcome, or other model assumption |
| `user_assumption` / `synthetic_demo` | Optional starting-price classifications for hypothetical scenarios |
| `forecast_model_output` / `model_output` | Simulated result, not a disclosed fact |

Earnings cases, starting weights, valuation multiples, market-condition price
adjustments, and selector settings are model assumptions. Historical issuer
figures provide a separate reference; they do not overwrite forward earnings
forecasts. The starting chart point inherits the starting-price classification.
Future chart values are model outputs.

## Events and historical returns

Business-event descriptions, timing, likelihoods, and outcomes are scenario
assumptions. A note referring to a date or milestone does not independently
verify the announcement or its future outcome.

Each calibration dataset has a defined date window and source basis. The
selected company must match its dataset and peer basket. Audit exports include
a dataset hash. Supplied histories and provider-sourced observations remain
explicitly distinguished in the source records.

## Listing units and currency

Each profile identifies its company, exchange, currency, and listed share or
ADS unit. Price and EPS must refer to the same unit. Saved scenario inputs stay
in their native currency; optional display conversion is recorded separately.
Provider observations are not issuer forecasts. Future curves and event outcomes
remain assumptions even when their historical references are public.

## Contributing and sharing

Include only public information and shareable model assumptions. Do not add
nonpublic customer details, confidential material, private financial plans, or
restricted third-party research. Calling confidential information an assumption
does not make it public. Personal holdings, tax plans, sale targets, and private
reports are outside the distributed package.

For a verified fact, cite the public issuer filing or release and record its
location, date, reporting period, units, and accounting basis. Check restatements.
Keep GAAP and non-GAAP figures and annual and quarterly periods distinct.
Announced plans and successful future execution are separate claims.

Validation checks structure, dates, ranges, and numerical consistency. It does
not certify the truth or public status of arbitrary notes or source URLs.
Custom notes appear in downloads. Local `outputs/`, `local-inputs/`, `.env` files,
and virtual environments are ignored by Git. Stage only reviewed files.
