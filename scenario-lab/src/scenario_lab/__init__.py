"""Scenario Lab public API; the original AMD API remains compatible."""
from importlib import import_module
import sys

from amd_scenario_lab import *
from amd_scenario_lab import __version__
from amd_scenario_lab.catalog import list_companies, get_company, company_info
from amd_scenario_lab.currency import for_display

for _module in ("config", "engine", "selector", "report", "catalog", "currency", "market_data", "cli"):
    sys.modules[f"{__name__}.{_module}"] = import_module(f"amd_scenario_lab.{_module}")
