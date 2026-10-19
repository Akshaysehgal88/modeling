# Sources and input records

Each company preset separates historical references from editable forecast
assumptions. Source records identify the issuer or provider, reporting period,
listing units, accounting basis, observation dates, and calibration window.

## Find a company's inputs

- [Company inputs, units, and sources](COMPANY_DATA.md) lists the 20 presets,
  issuer references, listing conventions, and data limitations.
- [Company demo files](../demos/) contain loadable scenarios named by preset ID.
- `src/scenario_lab/data/companies/` contains the company profiles, return
  samples, instrument catalog, and exchange-rate snapshot.
- `definitions.json` in that directory records the disclosed EPS bases and
  authored forecast assumptions used to prepare the provider-sourced profiles.
- Each run's `audit.json` records its inputs, source metadata, dataset hash,
  currency conversion, and runtime versions.

Issuer disclosures provide historical facts. Provider price, return, and
exchange-rate observations have a separate source basis. Future earnings,
valuation assumptions, event likelihoods, and event outcomes are scenarios,
not disclosed results or analyst consensus. The tool has no live data feed.

## Preset-specific source notes

### AMD: supplied scenario and calibration

This preset uses supplied forecast assumptions and a supplied return sample.
Those inputs are not independently verified public disclosures. Its historical
issuer EPS register is a separate background reference and does not replace its
forward earnings assumptions.

- `src/scenario_lab/data/amd_peer_history.csv`: 25 recorded rows, of which
  23 paired asset/peer returns from November 2024 through September 2026 are
  used for calibration. The first and final rows are outside that window.
- `demo.json` and `demos/AMD.json`: the same supplied starting price, annual
  EPS settings, three earnings cases, starting weights, market and funding
  parameters, 24 business-event rows, and monthly selection controls.
- `tests/fixtures/original_monthly.csv` and `original_selector.csv`: numerical
  reference outputs used for regression checks. They are simulated results,
  not evidence that future prices or scenarios occurred.

Event narratives and timing assertions remain forecast assumptions, including
references to dates or milestones that have not been independently checked.

### AMD: historical issuer references

Reviewed on **19 October 2026**. These historical EPS values are background
references and do not overwrite this preset's forward adjusted-EPS assumptions.

| Fact | Value | Publication | Location |
| --- | --- | --- | --- |
| FY2025 non-GAAP diluted EPS | $4.17 | 3 February 2026 | Annual Financial Results, 2025 non-GAAP EPS |
| FY2025 GAAP diluted EPS | $2.65 | 3 February 2026 | Annual Financial Results, 2025 GAAP EPS |
| Q2 2026 non-GAAP diluted EPS | $1.66 | 4 August 2026 | Non-GAAP Quarterly Financial Results, Q2'26 EPS |

Annual figures: AMD's [Fourth Quarter and Full Year 2025 Financial
Results](https://ir.amd.com/news-events/press-releases/detail/1276/amd-reports-fourth-quarter-and-full-year-2025-financial-results),
fiscal year ended 27 December 2025. Non-GAAP measures have an issuer reconciliation.

Quarterly figure: AMD's [Second Quarter 2026 Financial
Results](https://ir.amd.com/news-events/press-releases/detail/1295/amd-reports-second-quarter-2026-financial-results),
quarter ended 27 June 2026. This figure is not annualized or substituted into
forward scenarios.

Machine-readable background citations are stored in
`src/scenario_lab/data/public_facts.json`. Audit exports include the relevant
reference register and input-source records.
There is no live quote, news or financial-data feed.
