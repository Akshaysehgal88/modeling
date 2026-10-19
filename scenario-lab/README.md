# Scenario Lab

Explore equity scenarios for a curated set of 20 semiconductor and AI
infrastructure companies. Select a company, load its demo assumptions, and
explore earnings forecasts, business events, and monthly market conditions.

Every company uses the same simulation engine and interface, with its own
starting price, earnings assumptions, return history, and event inputs. The tool
includes interactive charts, native listing currencies, optional currency
conversion, and downloadable scenarios and results.

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

The **Company** control loads the selected company's demo. Earnings inputs,
business events, monthly market choices, charts, and downloads follow the same
workflow for every company. Each company's edits are kept separately during the
session, so switching back restores that company's working scenario.

For a first run, review **Starting point and earnings forecast**, optionally edit
the **Month-by-month market regime selector**, then click **Run scenario**. The
company demo is already loaded. File uploads are optional; a monthly CSV replaces
the monthly choices in a loaded JSON.

Enter annual base EPS once. **Alternative earnings cases and starting weights**
shows slowdown and acceleration as percentage differences from that base. Starting
weights must each be positive and total 100%. These percentages are only an editor
view: saved JSON stores EPS templates and fractional weights.

Optional advanced sections group valuation, funding, price swings, market condition
adjustments, the magenta line, and repeatability. Each numerical control explains
its purpose and scale. **Starting market condition** affects the full simulation;
monthly market choices affect only the magenta line. **Monthly business events and
outcomes** affect the full simulation. Starting price sources are kept separately.

This is a curated semiconductor and AI infrastructure focus list, not an
objective market-cap ranking or an investment recommendation.

Presets are listed alphabetically by ID.

| ID | Company | Listed instrument | Native currency |
| --- | --- | --- | --- |
| ADI | Analog Devices | ADI | USD |
| AMAT | Applied Materials | AMAT | USD |
| AMD | Advanced Micro Devices | AMD | USD |
| ARM | Arm Holdings | ARM | USD |
| ASML | ASML Holding | ASML.AS | EUR |
| AVGO | Broadcom | AVGO | USD |
| INTC | Intel | INTC | USD |
| KLAC | KLA Corporation | KLAC | USD |
| LRCX | Lam Research | LRCX | USD |
| MRVL | Marvell Technology | MRVL | USD |
| MU | Micron Technology | MU | USD |
| NVDA | NVIDIA | NVDA | USD |
| NXPI | NXP Semiconductors | NXPI | USD |
| QCOM | Qualcomm | QCOM | USD |
| SAMSUNG | Samsung Electronics | 005930.KS | KRW |
| SKHYNIX | SK hynix | 000660.KS | KRW |
| SNDK | SanDisk | SNDK | USD |
| STX | Seagate Technology | STX | USD |
| TSMC | Taiwan Semiconductor Manufacturing | 2330.TW | TWD |
| WDC | Western Digital | WDC | USD |

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

Each company has a loadable JSON file in [demos/](demos/), named by its preset ID.
Choose a company in the app to load its demo automatically, or load that file
when you want to start from a saved set of assumptions.

Each demo keeps historical references separate from forecasts:

- Starting prices and return histories have a recorded date and source basis.
- Historical EPS references retain their reporting period, accounting basis,
  currency, and listed-share units.
- Base, slowdown, and acceleration earnings forecasts, P/E assumptions, starting
  case weights, and event probabilities are editable model assumptions.
- Business-event dates and outcomes describe hypothetical scenarios to explore.

Public issuer references, provider observations, and supplied model inputs are
identified separately. Their exact coverage and any preset-specific exceptions
are documented in [Company inputs and sources](docs/COMPANY_DATA.md) and
[Sources and input records](docs/SOURCES.md). Forecast assumptions are authored
demos rather than analyst consensus or company guidance.

The bundled market snapshot is dated **16 October 2026**, with calibration
observations through September 2026. History lengths vary by company. Each
profile records its fiscal-year convention; the model blends annual EPS by
calendar month. The shared chart period runs from October 2026 to October 2028.

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

The chart shows a blue earnings reference, green median (P50), amber 80th
percentile (P80), magenta monthly selection, and a gray P10–P90 range. All
percentiles come from the same simulated price distribution.

**Match similar market conditions** (`conditioned` in JSON) selects monthly
weighted medians around one hypothetical market history. Those monthly prices
need not form one coherent trading path.
**Follow one simulated price path** (`path_rank` in JSON) follows one simulated
price path except where the percentile limits change it.
The model uses random seeds for reproducible results. Percentile bands are model ranks, not calibrated probabilities.

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
A company flag and supplied JSON must refer to the same company; mismatches are
rejected. Use the `scenario-lab` command and `scenario_lab` Python imports.
Everything needed to run the tool is contained in this `scenario-lab` folder.

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
