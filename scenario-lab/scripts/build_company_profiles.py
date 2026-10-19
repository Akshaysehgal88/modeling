"""Rebuild dated company demos from reviewed definitions and public market data.

Use --refresh to explicitly fetch public Yahoo Finance observations. Without it,
rebuild from the local ignored cache. The application itself runs offline.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src/amd_scenario_lab/data"
COMPANIES = DATA / "companies"
CACHE = ROOT / "outputs/market-cache"
AS_OF = "2026-10-16"
REVIEWED = "2026-10-19"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def fetch(symbol, interval, refresh):
    cutoff = datetime.fromisoformat(AS_OF).replace(tzinfo=timezone.utc)
    start = datetime(2024, 9, 1, tzinfo=timezone.utc) if interval == "1mo" else cutoff - timedelta(days=30)
    params = {"period1": int(start.timestamp()), "period2": int((cutoff + timedelta(days=2)).timestamp()),
              "interval": interval, "events": "div,splits"}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?{urlencode(params)}"
    file = CACHE / (symbol.replace("=", "_") + "_" + AS_OF + "_" + interval + ".json")
    if refresh or not file.exists():
        if not refresh:
            raise ValueError(f"Missing cache for {symbol}; explicitly use --refresh")
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 ScenarioLab research"})
        with urlopen(request, timeout=45) as response:
            raw = json.load(response)
        write_json(file, {"retrieved_on": datetime.now(timezone.utc).date().isoformat(), "response": raw})
    cached = json.loads(file.read_text(encoding="utf-8"))
    raw = cached["response"]
    if raw["chart"].get("error") or not raw["chart"].get("result"):
        raise ValueError(f"No market observations for {symbol}")
    result = raw["chart"]["result"][0]
    result["_retrieved_on"] = cached["retrieved_on"]
    zone = ZoneInfo(result["meta"]["exchangeTimezoneName"])
    dates = [datetime.fromtimestamp(t, zone).strftime("%Y-%m-%d") for t in result["timestamp"]]
    indicators = result["indicators"]
    field = indicators["adjclose"][0]["adjclose"] if interval == "1mo" else indicators["quote"][0]["close"]
    series = pd.Series(field, index=dates, dtype=float).dropna()
    if interval == "1mo":
        series.index = [d[:7] for d in series.index]
        # Yahoo can append a second, intramonth live bar. Neither partial bar
        # belongs in the completed-month calibration sample.
        series = series.loc[series.index < AS_OF[:7]]
    else:
        series = series.loc[series.index <= AS_OF]
    if not np.isfinite(series).all() or not (series > 0).all() or series.index.duplicated().any():
        raise ValueError(f"Invalid or duplicate completed market observations: {symbol}")
    return result, series, url


def build(refresh=False):
    catalog = json.loads((COMPANIES / "catalog.json").read_text(encoding="utf-8"))
    definitions = json.loads((COMPANIES / "definitions.json").read_text(encoding="utf-8"))
    entries = {c["id"]: c for c in catalog["companies"]}
    CACHE.mkdir(parents=True, exist_ok=True)
    observations = {}
    def get_company(entry):
        monthly = fetch(entry["symbol"], "1mo", refresh)
        daily = fetch(entry["symbol"], "1d", refresh)
        if monthly[0]["meta"]["currency"] != entry["currency"] or daily[0]["meta"]["currency"] != entry["currency"]:
            raise ValueError(f"Currency mismatch for {entry['id']}")
        if AS_OF not in daily[1].index:
            raise ValueError(f"Missing {AS_OF} closing observation: {entry['id']}")
        return entry["id"], (monthly, daily)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for key, value in pool.map(get_company, entries.values()):
            observations[key] = value
    legacy = json.loads((DATA / "demo.json").read_text(encoding="utf-8"))
    write_json(ROOT / "demos/AMD.json", legacy)
    rows = []
    for id, definition in definitions.items():
        entry = entries[id]
        monthly, daily = observations[id]
        returns = {}
        for member in [id, *definition["peers"]]:
            # Never forward-fill or substitute another instrument's returns.
            series = observations[member][0][1]
            returns[member] = series.pct_change(fill_method=None)
        frame = pd.DataFrame(returns).dropna()
        frame = frame.loc[(frame.index >= "2024-11") & (frame.index <= "2026-09")]
        if len(frame) < 12 or frame.index[-1] != "2026-09":
            raise ValueError(f"Insufficient complete paired history for {id}")
        peer = frame[definition["peers"]].mean(axis=1)
        history = pd.DataFrame({"month": frame.index, "asset_return": frame[id].to_numpy(),
                                "peer_return": peer.to_numpy()})
        history.to_csv(COMPANIES / f"{id}.csv", index=False, lineterminator="\n")
        fact = dict(definition["eps_base"])
        published = fact["published_on"] or f"{fact['year']}-12-31"
        split_divisor = 1.
        splits = monthly[0].get("events", {}).get("splits", {})
        for split in splits.values():
            split_date = datetime.fromtimestamp(split["date"], timezone.utc).strftime("%Y-%m-%d")
            if published < split_date <= AS_OF:
                split_divisor *= float(split["numerator"]) / float(split["denominator"])
        aligned_base = fact["value"] / split_divisor
        fact.update(split_divisor_since_publication=split_divisor, aligned_value=aligned_base)
        curves = {}
        for scenario, growth in definition["growth"].items():
            value = aligned_base
            curve = {str(fact["year"]): value}
            for year, change in zip(range(fact["year"] + 1, 2031), growth):
                value *= 1 + change
                curve[str(year)] = round(value, 4)
            curves[scenario] = {str(y): curve[str(y)] for y in range(2026, 2031)}
        # Shared mechanics use the preserved engine. These financial and event
        # inputs are rebuilt from this company's own facts and assumptions.
        config = json.loads(json.dumps(legacy))
        config.update(schema_version=3, title=f"{entry['name']} demo", company=entry,
                      scenario_eps=curves)
        price = float(daily[1].loc[AS_OF])
        config["anchor"] = dict(price=price, classification="public_observation", as_of=AS_OF,
                                source_url=daily[2], note="Dated public feed close for this listed instrument; native currency, split-adjusted listing units.")
        config["settings"].update({f"eps{y % 100}": curves["reference"][str(y)] for y in range(2026, 2031)})
        config["settings"].update(stabilized_forward_pe=definition["terminal_pe"],
                                  initial_credit_stress=definition["initial_credit_stress"],
                                  credit_long_run=definition["initial_credit_stress"] * .75,
                                  initial_regime=definition["initial_regime"])
        config["calibration"] = dict(dataset=f"companies/{id}.csv", window_start=frame.index[0],
                                     window_end=frame.index[-1], classification="public_market_data")
        cyclical = id in ("MU", "SNDK", "SAMSUNG", "SKHYNIX", "WDC", "STX")
        config["priors"] = [.35, .45, .20] if cyclical else [.25, .50, .25]
        config["price_levels"] = [round(price * factor, 4) for factor in (.8, 1., 1.2, 1.5, 2.)]
        events = []
        for i, month in enumerate(pd.period_range("2026-11", periods=24, freq="M")):
            driver = definition["drivers"][i % 3]
            reporting = month.month in definition["reporting_months"]
            events.append(dict(month=str(month),
                catalyst=f"{entry['name']}: " + ("earnings and outlook checkpoint; " if reporting else "operating checkpoint; ") + driver,
                upside_evidence=f"Improvement in {driver} versus the chosen reference scenario",
                downside_evidence=f"Deterioration in {driver} versus the chosen reference scenario",
                timing="Hypothetical reporting / monitoring window; no exact future announcement date asserted",
                prob_positive=.50 if cyclical else .55, revelation_chance=.85 if reporting else .45,
                materiality=.9 if reporting else .5, status="pending", classification="forecast_assumption"))
        config["events"] = events
        config["sources"] = dict(eps_base=fact,
            quote=dict(provider="Yahoo Finance public chart endpoint", url=daily[2], as_of=AS_OF, retrieved_on=daily[0]["_retrieved_on"],
                       currency=entry["currency"], unit=entry["unit"]),
            history=dict(provider="Yahoo Finance public chart endpoint", asset_url=monthly[2], retrieved_on=monthly[0]["_retrieved_on"],
                         peer_ids=definition["peers"], peer_urls={p: observations[p][0][2] for p in definition["peers"]},
                         observations=len(frame), adjustment="Split-and-dividend-adjusted monthly prices; local exchange months; simple returns; equal-weight native-return peer basket; complete observations only"))
        config["forecast_notes"] = dict(classification="forecast_assumption", rationale=definition["rationale"],
            annual_growth=definition["growth"], drivers=definition["drivers"],
            earnings_basis=entry["eps_basis"], fiscal_year_end=entry["fiscal_year_end"],
            calendar_approximation="Issuer fiscal-year labels feed the original calendar-month EPS interpolation; this is a scenario approximation, not a quarterly financial model.")
        write_json(COMPANIES / f"{id}.json", config)
        write_json(ROOT / f"demos/{id}.json", config)
        rows.append((id, entry["currency"], round(price, 3), fact["value"], len(frame)))
    fx = {"as_of": AS_OF, "retrieved_on": "", "base": "USD", "units_per_usd": {"USD": 1.}, "sources": {}}
    for currency, symbol in (("EUR", "EURUSD=X"), ("KRW", "KRW=X"), ("TWD", "TWD=X")):
        raw, values, url = fetch(symbol, "1d", refresh)
        if AS_OF not in values.index:
            raise ValueError(f"Missing dated FX observation: {symbol}")
        value = float(values.loc[AS_OF])
        fx["units_per_usd"][currency] = 1 / value if currency == "EUR" else value
        fx["sources"][currency] = url
        fx["retrieved_on"] = max(fx["retrieved_on"], raw["_retrieved_on"])
    write_json(COMPANIES / "fx.json", fx)
    print("Built profiles (id, currency, anchor, disclosed EPS base, paired monthly observations):")
    for row in rows:
        print(*row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Explicitly download public market observations")
    build(parser.parse_args().refresh)
