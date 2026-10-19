#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import scenario_lab, streamlit, plotly; assert scenario_lab.__version__ == "2.0.0"' >/dev/null 2>&1; then
  .venv/bin/python -m pip uninstall -y amd-scenario-lab >/dev/null 2>&1 || true
  .venv/bin/python -m pip install '.[ui]'
fi
exec .venv/bin/python -m scenario_lab ui
