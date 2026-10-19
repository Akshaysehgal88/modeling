"""AMD Scenario Lab: transparent, uncalibrated scenario research."""

from .config import demo_config, load_config, validate_config
from .engine import run_model
from .selector import SelectorConfig, compute_smart_selector

__version__ = "1.0.0"
__all__ = ["demo_config", "load_config", "validate_config", "run_model",
           "SelectorConfig", "compute_smart_selector"]
