# AMD Scenario Lab

A local research tool for exploring AMD earnings, valuation, credit conditions,
market regimes and an adaptive percentile overlay. Start with the demo, change
assumptions, and export a report anyone can open without Python.

**Every future earnings figure, event outcome, price and percentile is a forecast
assumption or model output.** The model is uncalibrated. Its percentile bands are
not market probabilities or confidence intervals, and the adaptive overlay does
not know future conditions.

## Quick start

Install Python 3.10 or newer. From this folder:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install ".[ui]"
amd-lab ui
```

Open the local address shown in the terminal, normally
[http://127.0.0.1:8501](http://127.0.0.1:8501). Select assumptions and click **Run
scenario**. The app binds to your own computer. Stop it with Ctrl+C.

Alternatively, double-click `run_windows.bat`, or run `bash run_mac_linux.sh`.
Those launchers create a folder-local virtual environment and install dependencies
on first use. Installation requires internet; simulation and report export do not.
No API key, subscription or live data connection is needed. The launcher does not
upgrade installed packages on subsequent runs.

## What the demo contains

| Input | Status |
| --- | --- |
| Historical annual GAAP and non-GAAP EPS | Public disclosed facts, with issuer URL, publication date, period and accounting basis |
| Historical quarterly non-GAAP EPS | Public fact for context only; not annualized |
| Starting price of $100 | **Synthetic demo value, not an AMD quote** |
| Annual EPS growth: 0%, 15%, 30% | **Illustrative forecast assumptions, not guidance or consensus** |
| P/E, volatility, credit, regimes, scenario weights | **Illustrative forecast assumptions; not estimated from market history** |
| Future event schedule | Empty by default; custom events are hypothetical forecast assumptions |
| All future chart points | **Model outputs**, including the earnings/P/E reference |

The public fact register is frozen and reviewed on **19 October 2026**. It is a
small teaching reference, not a complete or continuously updated financial dataset.
The quarterly fact does not replace the annual EPS base.

## Use your own scenario

```bash
amd-lab init scenario.json
amd-lab validate scenario.json
amd-lab run --config scenario.json --out outputs/my-scenario
```

`init` refuses to overwrite an existing file. Edit the JSON or load it through the
browser interface. Configuration validation rejects unknown fields, invalid
probabilities, nonfinite numbers and incompatible dates. It does **not** certify
that a custom URL or note is true or public.

For a real price anchor, choose `public_observation`, provide an HTTPS source URL
and its actual observation date, and align `start_month` with that date's month.
The application does not fetch or verify that quote. Otherwise keep
`synthetic_demo` or use `user_assumption`. A midmonth observation is treated as
the first monthly anchor; subsequent points represent the following monthly
scenario checkpoints, an explicit timing approximation.

Edit `annual_growth`, the three `priors` (sum to one), and `market` settings.
The annual EPS base must be one of the disclosed annual facts in the register.
All forward EPS figures are derived assumptions even when their starting value
is disclosed. Keep the valuation multiple consistent with GAAP or non-GAAP EPS.

Optional event example, inserted into `events`:

```json
{
  "month": "2027-02",
  "label": "Hypothetical earnings evidence checkpoint",
  "classification": "forecast_assumption",
  "prob_positive": 0.5,
  "revelation_chance": 0.8,
  "materiality": 0.7,
  "status": "pending"
}
```

There can be at most one event per future month. `pending` simulates an unknown
outcome. `positive` and `negative` force hypothetical outcomes for stress testing;
`neutral` supplies no evidence. These are not claims of actual announced events
or actual future observations. When changing the horizon, update custom event
months too. For a publicly announced future milestone, cite its announcement in
your working notes and still treat future completion and model probabilities as
assumptions; this version intentionally bundles no such milestones.

## Command-line demo without the browser

The core install needs only NumPy and pandas:

```bash
python -m pip install .
python -m amd_scenario_lab run --out outputs/demo
```

Output files:

- `report.html`: standalone, offline chart, tables, diagnostics and provenance.
- `monthly.csv`: earnings/P/E reference, P10/P25/P50/P75/P80/P90 and adaptive overlay.
- `selector.csv`: raw versus clipped ranks, market state and conditioning support.
- `audit.json`: complete scenario, configuration hash, source register and model limitations.

The report is self-contained; it makes no external script or data requests.
Repeated runs with identical configuration and dependency versions reproduce the
same results. `run` overwrites these four filenames in the chosen output folder.
Exports include custom configuration text: review it before sharing.

## How to read the chart

- **Blue:** projected EPS mixture multiplied by an assumed P/E reference.
- **Green:** monthly P50 across the shared simulated price distribution.
- **Amber:** monthly P80 across that same distribution.
- **Magenta:** an adaptive scenario overlay within P10-P90.
- **Gray:** P10-P90 model range, not an empirical 80% confidence interval.

In `conditioned` mode, one seeded hypothetical market history supplies credit,
regime, earnings-belief and sentiment conditions. Each month then selects a
weighted median across paths with similar conditions. This can jump between
months and is not a coherent individual price path. `path_rank` follows one
simulated price path, except where clipping to P10-P90 changes it. Neither mode
is a most-likely forecast or a trade instruction. Changing the selector seed
changes the overlay without changing the underlying price distribution.

## Python API

```python
from amd_scenario_lab import demo_config, run_model, compute_smart_selector
from amd_scenario_lab.report import export_result

config = demo_config()
config["seed"] = 123
result = run_model(config)
overlay = compute_smart_selector(result)
export_result(result, overlay, "outputs/python-demo")
```

## Development

```bash
python -m pip install -e ".[ui,dev]"
python -m pytest
python -m build
```

CI exercises numerical invariants, event conditioning, input validation, output
provenance, installed CLI behavior and Streamlit controls. The code uses a `src`
layout and includes its JSON resources in wheels.

Read [Methodology](docs/METHODOLOGY.md) for equations and limitations,
[Public data policy](docs/PUBLIC_DATA_POLICY.md) for the publication boundary,
and [Sources](docs/SOURCES.md) for the exact bundled disclosures.

MIT license applies to this project's code. AMD names belong to their owners.
Referenced issuer material remains subject to its owners' rights. This project
is independent of AMD.
