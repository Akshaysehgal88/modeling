"""Scenario Lab: company-specific equity simulations and monthly market controls."""

from .config import demo_config, load_config, validate_config
from .engine import run_model
from .selector import SelectorConfig, compute_smart_selector, blank_overrides

__version__ = "2.0.1"
__all__ = ["demo_config", "load_config", "validate_config", "run_model",
           "SelectorConfig", "compute_smart_selector", "blank_overrides", "list_companies", "get_company", "company_info", "for_display"]

from .catalog import list_companies, get_company, company_info
from .currency import for_display
