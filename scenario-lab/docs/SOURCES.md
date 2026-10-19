# Original AMD sources and input provenance

For all additional company presets, see [Company data and sources](COMPANY_DATA.md).

## Original model inputs

The packaged calibration CSV and demo configuration preserve the supplied AMD v3
research model's inputs. These are identified as user-supplied model inputs and
forecast assumptions; they are not independently verified public disclosures.

- `data/amd_peer_history.csv`: original 25-row history; the model calibrates on
  23 paired monthly AMD/peer returns from November 2024 through September 2026.
- `demo.json`: original anchor, annual EPS settings, three scenario templates,
  priors, regime premiums, credit/market parameters, all 24 evidence rows,
  selector configuration and monthly override controls.
- `tests/fixtures/original_monthly.csv` and `original_selector.csv`: nonpersonal
  numerical reference outputs used for regression checks. They are model outputs,
  not evidence that future prices or scenarios occurred.

Original event timing narratives are retained as assumptions. Wording about
confirmed dates or milestones has not been independently checked. No personal
holdings, sale targets, tax settings or personal reports are included.

## Separate public fact register

Reviewed on **19 October 2026**. These historical EPS values are background
references and do not overwrite the model's forward adjusted-EPS assumptions.

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

Machine-readable public citations remain in `data/public_facts.json`. Audit
exports include both that register and the distinct original-input provenance.
There is no live quote, news or financial-data feed.
