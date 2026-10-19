"""Instrument identities and independent, offline company presets."""
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
import json


def read_data(name):
    return json.loads(files("scenario_lab").joinpath("data/" + name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _catalog():
    return read_data("companies/catalog.json")


def list_companies():
    return deepcopy(_catalog()["companies"])


def get_company(company_id):
    for entry in _catalog()["companies"]:
        if entry["id"] == company_id:
            return deepcopy(entry)
    raise ValueError(f"Unknown company: {company_id}")


def company_info(config):
    return get_company(config["company"]["id"] if config.get("schema_version") == 3 else "AMD")


def company_demo(company_id="AMD"):
    get_company(company_id)  # Reject unknown identifiers; never fall back to AMD.
    return read_data("demo.json" if company_id == "AMD" else f"companies/{company_id}.json")


def company_facts(config):
    company = company_info(config)
    if company["id"] == "AMD":
        return read_data("public_facts.json")
    fact = deepcopy(config["sources"]["eps_base"])
    fact["period"] = f"FY{fact['year']}"
    return {"reviewed_on": "2026-10-19", "company": company,
            "facts": [fact],
            "scope": "Disclosed EPS reference for this instrument; forward curves remain forecast assumptions."}
