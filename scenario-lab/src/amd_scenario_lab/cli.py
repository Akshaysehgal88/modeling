"""Command-line entry point and local UI launcher."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .config import NOTICE, demo_config, load_config
from .catalog import list_companies, company_info
from .currency import for_display, SYMBOLS


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scenario Lab - company-specific scenarios and monthly regime controls")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Write an editable demo configuration")
    init.add_argument("path", nargs="?", default="scenario.json")
    ids = [c["id"] for c in list_companies()]
    init.add_argument("--company", type=str.upper, choices=ids, default="AMD")
    commands.add_parser("companies", help="List the 20 company presets, listings and native currencies")
    validate = commands.add_parser("validate", help="Validate a scenario JSON file")
    validate.add_argument("config")
    run = commands.add_parser("run", help="Generate CSV, audit JSON and standalone HTML")
    run.add_argument("--config", help="Scenario JSON; omit for the original demo")
    run.add_argument("--out", help="Output folder; defaults to outputs/demo for AMD or outputs/COMPANY")
    run.add_argument("--company", type=str.upper, choices=ids, help="Company preset; AMD by default")
    run.add_argument("--currency", choices=list(SYMBOLS), help="Optional display/export currency; native by default")
    run.add_argument("--fx-rate", type=float, help="Display currency per one native currency unit; dated reference by default")
    run.add_argument("--overrides", help="Monthly regime CSV with 24 future rows or all 25 chart points")
    ui = commands.add_parser("ui", help="Open the local browser interface (requires [ui] extra)")
    ui.add_argument("--port", type=int, default=8501)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            with Path(args.path).open("x", encoding="utf-8") as f:
                json.dump(demo_config(args.company), f, indent=2, allow_nan=False)
                f.write("\n")
            print(f"Created {Path(args.path).resolve()}. Edit forecast assumptions before running.")
        elif args.command == "companies":
            for c in list_companies():
                print(f"{c['id']:8} {c['symbol']:12} {c['currency']:3} {c['exchange']:20} {c['name']}")
        elif args.command == "validate":
            load_config(args.config)
            print("Valid scenario. Source URLs are assertions; validation does not verify custom facts.")
        elif args.command == "run":
            from .engine import run_model
            from .report import export_result
            from .selector import compute_smart_selector
            c = load_config(args.config) if args.config else demo_config(args.company or "AMD")
            if args.company and company_info(c)["id"] != args.company:
                raise ValueError("--company does not match the supplied scenario JSON")
            if args.overrides:
                import pandas as pd
                rows = pd.read_csv(args.overrides).fillna("")
                if "notes" not in rows:
                    rows["notes"] = ""
                if len(rows) == 24:
                    rows = pd.concat([pd.DataFrame([c["monthly_overrides"][0]]), rows], ignore_index=True)
                c["monthly_overrides"] = rows.to_dict("records")
            result = run_model(c)
            selector = compute_smart_selector(result)
            info = company_info(c)
            view, selected = for_display(result, selector, args.currency, args.fx_rate)
            directory = export_result(view, selected, args.out or ("outputs/demo" if info["id"] == "AMD" else f"outputs/{info['id']}"))
            print(f"Company: {info['name']} ({info['symbol']}); native {info['currency']}; display {view['display']['currency']}")
            print(NOTICE)
            print(f"Anchor: {result['config']['anchor']['classification']}")
            print(f"Report: {(directory / 'report.html').resolve()}")
        else:
            if not 1024 <= args.port <= 65535:
                raise ValueError("port must be between 1024 and 65535")
            from importlib.util import find_spec
            if find_spec("streamlit") is None or find_spec("plotly") is None:
                raise ValueError('Install the UI extra first: python -m pip install ".[ui]"')
            environment = os.environ.copy()
            environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
            environment["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
            raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run",
                str(Path(__file__).with_name("app.py")), "--server.address=127.0.0.1",
                f"--server.port={args.port}", "--browser.gatherUsageStats=false"], env=environment))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")
