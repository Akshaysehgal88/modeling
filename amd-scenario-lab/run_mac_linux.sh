#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import amd_scenario_lab, streamlit, plotly; assert amd_scenario_lab.__version__ == "1.1.0"' >/dev/null 2>&1; then
  .venv/bin/python -m pip install '.[ui]'
fi
exec .venv/bin/python -m amd_scenario_lab ui
