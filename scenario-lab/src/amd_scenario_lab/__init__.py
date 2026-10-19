"""AMD Scenario Lab: the preserved original model with monthly controls."""

from .config import demo_config, load_config, validate_config
from .engine import run_model
from .selector import SelectorConfig, compute_smart_selector, blank_overrides

__version__ = "2.0.0"
__all__ = ["demo_config", "load_config", "validate_config", "run_model",
           "SelectorConfig", "compute_smart_selector", "blank_overrides"]

from .catalog import list_companies, get_company
