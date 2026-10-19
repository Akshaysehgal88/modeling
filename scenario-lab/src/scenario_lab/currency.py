"""Currency presentation only; simulations and saved assumptions stay native."""
from copy import deepcopy
import math

from .catalog import company_info, read_data

SYMBOLS = {"USD": "$", "EUR": "€", "KRW": "₩", "TWD": "NT$"}
PRICE_COLUMNS = {"blue_earnings_reference", "orange_optimistic_p80", "green_integrated_median",
                 "earnings_reference", "reference_expected_eps", "reference_eps",
                 "p10", "p25", "p50", "p75", "p80", "p90"}
SELECTOR_PRICES = {"smart_selected_price", "raw_joint_scenario_price", "p10", "p50", "p80", "p90",
                   "underlying_joint_scenario_price", "selected_price", "raw_price"}


def fx_snapshot():
    return read_data("companies/fx.json")


def reference_rate(native, target):
    rates = fx_snapshot()["units_per_usd"]
    if native not in rates or target not in rates:
        raise ValueError("Unsupported currency")
    return rates[target] / rates[native]


def currency_context(result):
    native = company_info(result["config"])["currency"]
    return result.get("display", {"currency": native, "native_currency": native, "rate": 1.,
                                   "as_of": None, "classification": "native_currency"})


def for_display(result, selector, target=None, rate=None):
    native = company_info(result["config"])["currency"]
    target = native if target is None else target
    expected = reference_rate(native, target)
    rate = expected if rate is None else rate
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
        raise ValueError("FX rate must be finite and positive")
    if native == target and rate != 1:
        raise ValueError("A native-currency display must use rate 1")
    view = dict(result)
    view["monthly"] = result["monthly"].copy()
    selected = selector.copy()
    if rate != 1:
        for key in PRICE_COLUMNS.intersection(view["monthly"].columns):
            view["monthly"][key] *= rate
        for key in SELECTOR_PRICES.intersection(selected.columns):
            selected[key] *= rate
        view["paths"] = result["paths"] * rate
    view["meta"] = deepcopy(result["meta"])
    view["display"] = {"currency": target, "native_currency": native, "rate": rate,
                       "as_of": fx_snapshot()["as_of"] if target != native else None,
                       "classification": ("native_currency" if target == native else
                                          "public_market_data" if math.isclose(rate, expected, rel_tol=1e-12) else "user_assumption"),
                       "source": fx_snapshot() if target != native else None}
    return view, selected
