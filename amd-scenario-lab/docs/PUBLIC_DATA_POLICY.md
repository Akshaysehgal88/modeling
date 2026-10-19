# Public data and forecasting policy

This package was rebuilt from an AMD research prototype using an explicit
allowlist. Original archives, generated HTML/images/CSV outputs, local paths,
portfolio settings, tax calculations, unverified histories, original earnings
forecasts and unsourced customer/milestone narratives were not imported.

## Publication boundary

The only bundled company-specific numerical facts are in
`src/amd_scenario_lab/data/public_facts.json`. Each has a public issuer source,
publication date, reporting period, accounting basis and a precise table location.
Only selected numbers are recorded; no entire source documents are redistributed.

The clean demo configuration has no portfolio size, sale objective, tax rate,
private financial plan, customer contract detail or proprietary analyst estimate.
The market model uses synthetic Gaussian innovations rather than the prototype's
unsourced peer-return history. No terminal or paywalled research is bundled.

## Classifications

| Classification | Meaning |
| --- | --- |
| `public_disclosed_fact` | Historical fact manually checked in a publicly accessible issuer disclosure |
| `public_observation` | Custom price anchor with a user-provided public source; not independently verified by the app |
| `synthetic_demo` | Artificial demo anchor, not an observed security price |
| `user_assumption` | User-entered starting anchor with no verified public-fact claim |
| `forecast_assumption` | Forward growth, event, outcome or other modeling hypothesis |
| `forecast_model_output` / `model_output` | Derived simulated result, not a disclosed fact |

All numeric market parameters, priors, fixed method coefficients and selector
settings are forecast/model assumptions, even where the JSON groups those
parameters instead of repeating the classification on every value. Dates and
seeds are scenario controls. The UI, methodology and every exported report state
this distinction. Only the initial chart point inherits the anchor classification.

Relabeling confidential information as an assumption does not make it publishable.
Do not add nonpublic customer details, unpublished forecasts, private account
information or restricted research to this repository. The software cannot
determine whether arbitrary user text or numbers are confidential. Custom inputs
and exports stay local unless the user shares or commits them.

## Updating facts

1. Use an original public issuer filing or earnings release.
2. Record period, units, basis, exact source location, publication date and review date.
3. Verify the numerical value and check whether it was restated.
4. Keep quarterly EPS separate from annual EPS. Do not mix GAAP and non-GAAP figures.
5. Keep guidance separate from historical facts. Publicly announced future plans
   do not guarantee future delivery or turn assumed probabilities into facts.
6. Review the diff and run the tests before publishing.

`validate` checks structure and ranges, not source authenticity. A URL is not
proof that a claim appears on that page. No heuristic scanner can guarantee that
future contributions contain no confidential information; manual source review
remains required.

Local `outputs/`, `local-inputs/`, virtual environments and `.env` files are
ignored by Git. Explicitly stage only reviewed source files.
