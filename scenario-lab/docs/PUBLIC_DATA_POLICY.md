# Scenario Lab input and publication policy

The package preserves the supplied AMD model, including its forecast assumptions,
calibration sample, evidence windows and adaptive selector. Personal portfolio, proceeds, personal currency/tax planning and personal-context
material are excluded. Generic instrument-currency presentation is supported. The original archive and original personal reports are not distributed.

## Classifications

| Classification | Meaning |
| --- | --- |
| `public_disclosed_fact` | Historical issuer figure with a manually reviewed public source |
| `user_supplied_snapshot` | Original scenario anchor; not independently verified by this package |
| `user_supplied_model_input` | Original paired-return calibration series; not independently source-verified |
| `forecast_assumption` | Earnings curve, event window, likelihood, outcome or other model hypothesis |
| `public_observation` | Custom anchor with a user-provided HTTPS source; the application does not verify it |
| `user_assumption` / `synthetic_demo` | Optional custom anchor classifications |
| `forecast_model_output` / `model_output` | Simulated result, not a disclosed fact |

Settings, priors, scenario EPS templates, regime premiums and selector settings
are model/forecast assumptions. They remain in the JSON and in the calculation.
This labeling does not change their numerical values. The initial chart point
inherits the anchor classification; future chart values are model outputs.

The historical issuer register is a separate reference dataset. It does not
constrain or overwrite the original forward EPS assumptions. This is deliberately
a scenario tool rather than a model restricted to already reported figures.

## Event and calibration handling

The original event narratives are retained as scenario notes. Their timing text
may refer to announced dates, milestones or customer plans; these assertions
have not been independently verified in this package. The entire row is labeled
as a forecast assumption. This preserves the original scenario without promoting
its narrative into verified fact. Future outcomes and likelihoods remain assumptions.

`data/amd_peer_history.csv` is the original nonpersonal paired-return input.
Its provenance is user-supplied. The November 2024-September 2026 subset is used
for calibration exactly as in the original. The full 25-row source is retained;
the first and final rows lie outside that calibration window. A source hash is
included in audit exports.

## Contributing and sharing

Do not add nonpublic customer details, confidential information, private financial
plans or restricted third-party research. Labeling confidential material as an
assumption does not make it public. The existing original model assumptions are
included at the user's direction; custom inputs still require their own review.

For a new verified fact, cite an original public issuer filing or release, record
the exact location, date, period, units and accounting basis, and check restatements.
Keep GAAP and non-GAAP figures and annual/quarterly periods distinct. Publicly
announced future plans are separate from successful future execution.

Validation checks structure, date coverage, ranges and numerical consistency;
it does not certify the public status or truth of arbitrary text or source URLs.
Custom notes are included in downloads. Local `outputs/`, `local-inputs/`, `.env`
files and virtual environments are ignored by Git. Stage only reviewed files.


## Additional company presets

Nineteen additional company profiles use public issuer EPS references and dated
public market observations, with explicit company-specific forecast assumptions.
They are not copies of the original AMD earnings, quote, history or event rows.
The classification `public_market_data` denotes provider-sourced quote/return/FX
observations; `public_observation` identifies a dated anchor. Provider data is not
an issuer forecast. `forecast_assumption` continues to identify authored future
curves, outcomes and likelihoods.

Each profile binds company, exchange, currency and share/ADS unit. Price and EPS
must refer to the same listed unit. Native inputs remain native in saved scenarios;
optional display conversion is recorded separately. Source URLs, disclosure basis,
retrieval dates, dataset hashes and version metadata remain inspectable. No
nonpublic data or personal finance information has been introduced.
