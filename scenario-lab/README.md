# Scenario Lab

Select a company and run the same earnings, evidence, credit, market-regime and
adaptive-percentile model. The interface includes **20 company demos**, native
listing currencies and optional display conversion.

Choosing **AMD** loads the preserved original model, assumptions, calibration,
monthly controls and four-line chart. Its default results still reproduce the
original supplied outputs. Other companies load their own public quote and
return history, EPS reference, forecast curves and evidence checklist.

## Start

Install Python 3.10+. Open this `scenario-lab` folder, then double-click
`run_windows.bat` on Windows or run `bash run_mac_linux.sh` on macOS/Linux.
The launcher installs dependencies on first use and migrates an older local
installation. Installation needs internet; simulations run offline.

Manual setup:

```bash
python -m venv .venv
```

Activate `.venv\Scripts\Activate.ps1` in Windows PowerShell or
`source .venv/bin/activate` on macOS/Linux, then:

```bash
python -m pip install ".[ui]"
scenario-lab ui
```

Open the local address printed in the terminal, normally
[http://127.0.0.1:8501](http://127.0.0.1:8501). Stop with Ctrl+C. The application
binds to your own computer and needs no API key or market-data subscription.

## Select a company

The **Company** control sits above the existing workflow. It loads the selected
company's demo. The inputs, evidence editor, monthly regime selector, original
chart layout and diagnostics follow the same flow for every company. Edits are
kept separately within each company's session; switching back to AMD restores
its working scenario rather than copying another company's edits into it.

For a first run, review **Starting point and earnings forecast**, optionally edit
the **Month-by-month market regime selector**, then click **Run scenario**. The
company demo is already loaded. File uploads are optional; a monthly CSV replaces
the monthly choices in a loaded JSON.

Enter annual base EPS once. **Alternative earnings cases and starting weights**
shows slowdown and acceleration as percentage differences from that base. Starting
weights must each be positive and total 100%. These percentages are only an editor
view: saved JSON retains the original EPS templates and fractional weights.

Optional advanced sections group valuation, funding, price swings, market condition
adjustments, the magenta line, and repeatability. Each numerical control explains
its purpose and scale. **Starting market condition** affects the full simulation;
monthly market choices affect only the magenta line. **Monthly business events and
outcomes** affect the full simulation. Starting price sources are kept separately.

This is a curated semiconductor and AI infrastructure focus list, not an
objective market-cap ranking or an investment recommendation.

| ID | Company | Listed instrument | Native currency |
| --- | --- | --- | --- |
| AMD | Advanced Micro Devices | AMD | USD |
| NVDA | NVIDIA | NVDA | USD |
| AVGO | Broadcom | AVGO | USD |
| INTC | Intel | INTC | USD |
| QCOM | Qualcomm | QCOM | USD |
| MU | Micron Technology | MU | USD |
| SNDK | SanDisk | SNDK | USD |
| WDC | Western Digital | WDC | USD |
| STX | Seagate Technology | STX | USD |
| MRVL | Marvell Technology | MRVL | USD |
| TSMC | Taiwan Semiconductor Manufacturing | 2330.TW | TWD |
| SAMSUNG | Samsung Electronics | 005930.KS | KRW |
| SKHYNIX | SK hynix | 000660.KS | KRW |
| ASML | ASML Holding | ASML.AS | EUR |
| AMAT | Applied Materials | AMAT | USD |
| LRCX | Lam Research | LRCX | USD |
| KLAC | KLA Corporation | KLAC | USD |
| ARM | Arm Holdings | ARM | USD |
| ADI | Analog Devices | ADI | USD |
| NXPI | NXP Semiconductors | NXPI | USD |

Samsung and SK hynix use their Korean **ordinary shares in KRW**. TSMC uses
**2330.TW ordinary shares in TWD**, rather than mixing an ADR price with ordinary
share EPS. ASML uses its **Amsterdam EUR listing**. Arm uses its Nasdaq USD ADS;
one ADS represents one ordinary share. The remaining presets use their listed
USD share units.

## Currency

Inputs and simulations always use the instrument's native currency. The
**Display currency** control offers USD, EUR, KRW and TWD. Converting a view changes
only displayed/exported prices and EPS amounts; it does not change simulated
returns, regimes, P/E ratios, beliefs or percentile choices.

Conversion uses a dated public FX reference from **16 October 2026**, or an edited
rate expressed as display-currency units per one native-currency unit. It is a
fixed presentation conversion, not a forecast of future FX. Exports identify the
native currency, display currency and rate. Scenario JSON remains in native units;
`audit.json` also records the chosen display conversion.

## Demos and assumptions

Each company has a loadable file in [demos/](demos/), such as
[AMD](demos/AMD.json), [NVIDIA](demos/NVDA.json), [SanDisk](demos/SNDK.json),
[Samsung](demos/SAMSUNG.json) and [SK hynix](demos/SKHYNIX.json).
`demo.json` remains the original AMD preset for compatibility.

For the 19 new presets:

- Historical EPS comes from a cited issuer release or original filing, retaining
  its annual period, accounting basis and listed-share units.
- The anchor is the selected instrument's public **16 October 2026** close.
- Calibration uses its own split/dividend-adjusted monthly returns and an explicit
  five-company peer basket. No AMD return series is substituted.
- Year-specific reference/slowdown/acceleration earnings, P/E, priors and event
  probabilities are **authored demo assumptions**, not analyst consensus or
  company guidance. They are inspectable and editable.
- Evidence checkpoints describe company-specific business drivers; their future
  dates and outcomes are hypothetical.

Most presets have 23 paired monthly observations through September 2026. SanDisk
has 19 complete pairs in the public feed; the shorter history is kept explicitly,
with no filled or borrowed returns. KLA's EPS base reflects its 2026 ten-for-one
split. Samsung's EPS base is consolidated diluted **ordinary-share** EPS, not its
standalone-company or preference-share figure. ASML's EPS reference is explicitly
basic; Intel uses its disclosed non-GAAP EPS rather than turning a GAAP loss into
a positive reported result.

Issuer fiscal calendars differ. Each profile records its fiscal-year convention;
the unchanged core uses its original calendar-month interpolation of annual EPS.
That approximation remains a modeling assumption. The simulation grid stays
October 2026 through October 2028, preserving the original AMD flow.

## Monthly regime selector

For each forecast month choose **Auto**, Severe panic, Risk-off, Neutral,
Optimistic or Euphoric. Set a percentile from **10 to 90** to override selection;
**a blank cell** uses Auto or the selected regime in the app. CSV/JSON still use
**0** for this choice. An entered percentile takes precedence over the condition
and must lie within the magenta line's limits (10–90 by default).
Click **Run scenario** to apply edits.

Monthly choices alter only the magenta overlay. They never rewrite the underlying
price paths or force simulated regime transitions. A manually chosen regime with
too few supporting paths produces an error. Increase paths or choose another
regime. The initial anchor is fixed in this table.

Download the complete scenario JSON, or download/reload the monthly regime CSV.
The CSV supports all 25 chart points or just 24 future months. Required columns
are `month`, `market_condition`, `manual_percentile`; `notes` is optional on import.

## Read the chart

The original layout and colors remain: blue EPS/P-E reference, green integrated
P50, amber P80, magenta adaptive selection and a gray P10-P90 range. All quantiles
come from the same simulated price distribution.

**Match similar market conditions** (`conditioned` in JSON) selects monthly
weighted medians around one hypothetical market history. Those monthly prices
need not form one coherent trading path.
**Follow one simulated price path** (`path_rank` in JSON) follows one simulated
price path except where the percentile limits change it.
The model remains seeded and reproducible, with no added smoothing or calendar
turning points. Percentile bands are model ranks, not calibrated probabilities.

## Command line

```bash
scenario-lab companies
scenario-lab init my-nvidia.json --company NVDA
scenario-lab run --company NVDA --out outputs/nvidia
scenario-lab run --company SAMSUNG --currency USD --out outputs/samsung-usd
scenario-lab validate my-nvidia.json
scenario-lab run --config my-nvidia.json --overrides monthly_overrides.csv --out outputs/custom
```

`--fx-rate` can override the display conversion. `init` refuses to overwrite a file.
A company flag and supplied JSON must agree; the tool rejects mismatches instead
of silently falling back to AMD. The legacy `amd-lab` command and
`amd_scenario_lab` Python imports still work.

The five output files are `report.html`, `monthly.csv`, `selector.csv`,
`monthly_overrides.csv` and `audit.json`. Reports work offline. Audit records
include full native inputs, instrument identity, source URLs, calibration hash,
runtime versions, configuration hash and display FX. Custom notes are exported;
review them before sharing. Existing filenames in an output folder are overwritten.

## Python

```python
from scenario_lab import demo_config, run_model, compute_smart_selector
from scenario_lab.currency import for_display
from scenario_lab.report import export_result

config = demo_config("SAMSUNG")
config["monthly_overrides"][5]["manual_percentile"] = 80.0
result = run_model(config)
overlay = compute_smart_selector(result)
view, selected = for_display(result, overlay, "USD")
export_result(view, selected, "outputs/samsung")
```

## Development and source maintenance

```bash
python -m pip install -e ".[ui,dev]"
python -m pytest
python -m build
```

Data is a frozen snapshot, not a live feed. Reviewed EPS references and authored
forecast parameters are in `data/companies/definitions.json`. Instrument units are
in `catalog.json`. `scripts/build_company_profiles.py --refresh` explicitly
retrieves the dated public market observations; without `--refresh` it rebuilds
from an ignored local cache. Review disclosures, corporate actions, dates and
forecast assumptions before changing a snapshot. Running the app never refreshes
or fetches market data.

Read [Company data and sources](docs/COMPANY_DATA.md),
[Methodology](docs/METHODOLOGY.md), and [Input policy](docs/PUBLIC_DATA_POLICY.md).
The code is MIT licensed. Referenced issuer material and provider data retain
their owners' rights. This project is independent of the listed companies.
