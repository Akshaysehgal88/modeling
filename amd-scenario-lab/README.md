# AMD Scenario Lab

A local interface and Python package around the **original AMD v3 research
model**: annual earnings scenarios, monthly evidence updates, paired-return
calibration, credit dynamics, market regimes, momentum, sentiment and the adaptive
percentile selector. The original assumptions are included in [demo.json](demo.json).

Personal holdings, sale targets, currency conversion, tax assumptions and personal
context are excluded. Forecast assumptions remain part of the model; they are not
replaced by historical disclosed EPS or generic random shocks.

## Start the tool

Install Python 3.10+. Double-click `run_windows.bat` on Windows, or run
`bash run_mac_linux.sh` on macOS/Linux. The launchers create a local virtual
environment and install dependencies if needed. Installation requires internet;
the model runs locally without API keys or live data access.

For an existing installation, update it after pulling changes:

```bash
python -m pip install --upgrade ".[ui]"
amd-lab ui
```

For a fresh manual installation:

```bash
python -m venv .venv
```

Activate `.venv\Scripts\Activate.ps1` in Windows PowerShell or
`source .venv/bin/activate` on macOS/Linux, then run the installation commands
above. Open the local address shown in the terminal, normally
[http://127.0.0.1:8501](http://127.0.0.1:8501). Stop with Ctrl+C.

## Monthly regime selector

The browser shows a **Month-by-month market regime selector** table with one row
for each forecast month. Choose:

- **Auto:** the original conditional selector for that month's simulated conditions.
- **Severe panic / Risk-off / Neutral / Optimistic / Euphoric:** a regime override
  for that month's conditional selection.
- **Percentile:** 0 uses Auto or the selected regime; 10 through 90 forces a
  percentile. A forced percentile takes precedence over the regime choice.
- **Notes:** optional scenario notes saved with the configuration.

Click **Run scenario** to apply changes. These controls change the magenta overlay,
not the underlying simulated distribution. A manual regime with too few supporting
paths produces a clear error; increase paths or choose another regime. The
October 2026 anchor is fixed and cannot be overridden through the monthly table.

Download the complete **scenario JSON** to preserve all inputs, including monthly
choices. Download **monthly regime CSV** to edit only those choices in a spreadsheet,
and reload it through the sidebar. CSVs can contain all 25 chart points or just
the 24 future months. Required columns: `month`, `market_condition`,
`manual_percentile`; `notes` is optional on import.

## Original assumptions included

| Component | Restored default |
| --- | --- |
| Price anchor | $528.75, dated 16 October 2026; original user-supplied snapshot |
| Reference adjusted EPS, FY2026-2030 | 7.72, 16.07, 23.48, 29.19, 42.37 |
| Slowdown EPS template | 7.72, 11.80, 15.50, 19.00, 24.00 |
| Acceleration EPS template | 7.72, 19.30, 33.72, 48.54, 64.85 |
| Slowdown/reference/acceleration priors | 25% / 55% / 20% |
| Calibration | Original 23 paired monthly AMD/peer returns, November 2024-September 2026 |
| Evidence | All original 24 monthly evidence windows, likelihoods, arrival chances and materialities |
| Market state | Original credit, regime hazards, peer/idiosyncratic shocks, momentum and look-through dynamics |
| Selector | Original conditional weights, bandwidths, seed and P10-P90 bounds |
| Simulation | 6,000 paths; model seed 20261018; selector seed 20261019 |
| Horizon | Original October 2026 anchor through October 2028 |

The model uses its original fixed dates and five-year EPS structure. Refreshing
that timeline requires updating the model and data together. No live-data refresh
is implied. All assumptions can be inspected in the JSON; settings, scenario
curves, priors, premiums, evidence rows and monthly choices have browser controls.
The bundled calibration CSV remains the original sample.

Scenario EPS templates set slowdown/acceleration **ratios around the edited annual
reference EPS**, scaled by `earnings_scenario_spread`, exactly as in the original.
Changing a template's reference row alone does not overwrite the five reference
EPS settings; it changes the ratio denominator.

## Command-line use

```bash
amd-lab run --config demo.json --out outputs/demo
amd-lab init my-scenario.json
amd-lab validate my-scenario.json
amd-lab run --config my-scenario.json --overrides monthly_overrides.csv --out outputs/custom
```

`init` refuses to overwrite an existing file. `run` overwrites its five output
filenames in the selected output folder:

- `report.html`: standalone offline chart, output tables and provenance.
- `monthly.csv`: original monthly model outputs, export aliases and adaptive overlay.
- `selector.csv`: original selector diagnostics and export aliases.
- `monthly_overrides.csv`: the monthly controls used in this run.
- `audit.json`: full configuration, calibration/source metadata, runtime versions and configuration hash.

Core-only use requires NumPy and pandas: `python -m pip install .` then
`python -m amd_scenario_lab run`. HTML reports have no external script or data
requests. Exports include custom notes; review them before sharing.

## Read the chart

Blue is the original EPS/P-E reference; green is P50 and amber is P80 of the same
simulated price distribution. Magenta is the adaptive monthly selection inside
the gray P10-P90 envelope. The original chart presentation is retained.

In `conditioned` mode, one seeded hypothetical market history supplies monthly
credit, regime, earnings beliefs and sentiment. The selector computes each
month's conditional weighted median across paths with comparable conditions.
Those monthly values need not be one coherent traded-price path. `path_rank`
follows a sampled price path except where percentile clipping changes it.

The model is stochastic but reproducible with the same inputs and dependency
versions. Regime transitions and innovations are part of the original model,
not newly added randomness. Percentile bands remain within-model ranks rather
than empirically calibrated market probabilities or confidence intervals.

## Provenance and validation

The original anchor and paired-return history are retained as **user-supplied
model inputs**. They are not relabeled as independently verified public facts.
Event descriptions and timing notes are original **scenario assumptions**, even
where their original wording refers to confirmed dates or disclosed milestones.
Forward EPS values, likelihoods and market parameters are forecast assumptions.
The separate historical issuer fact register provides background references and
does not replace the original earnings curves.

Regression checks compare all numeric columns against both original supplied CSV
outputs. The restored defaults reproduce their monthly comparison and selector
diagnostics. The full numerical engine is preserved; only personal finance fields
and their proceeds/target calculations have been removed from it.

The configuration uses **schema version 2**. Configurations from the earlier
simplified package are not silently reinterpreted. Start with `demo.json` or
`amd-lab init` to use the restored original model.

## Python API

```python
from amd_scenario_lab import demo_config, run_model, compute_smart_selector
from amd_scenario_lab.report import export_result

config = demo_config()
config["monthly_overrides"][5]["market_condition"] = "Risk-off"
config["monthly_overrides"][8]["manual_percentile"] = 80.0
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

Tests cover original-output regression, numerical invariants, monthly overrides,
rare-regime handling, JSON/CSV round trips, browser table edits and provenance.
See [Methodology](docs/METHODOLOGY.md), [Input policy](docs/PUBLIC_DATA_POLICY.md)
and [Sources](docs/SOURCES.md). MIT license covers project code; issuer material
and AMD trademarks remain subject to their owners' rights. This project is
independent of AMD.
