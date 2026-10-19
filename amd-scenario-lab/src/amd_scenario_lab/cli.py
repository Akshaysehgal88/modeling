"""Command-line entry point and local UI launcher."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .config import NOTICE, demo_config, load_config


def main(argv=None):
    parser = argparse.ArgumentParser(description="AMD Scenario Lab - explicit forecast assumptions, public-source facts")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Write an editable demo configuration")
    init.add_argument("path", nargs="?", default="scenario.json")
    validate = commands.add_parser("validate", help="Validate a scenario JSON file")
    validate.add_argument("config")
    run = commands.add_parser("run", help="Generate CSV, audit JSON and standalone HTML")
    run.add_argument("--config", help="Scenario JSON; omit for the synthetic demo")
    run.add_argument("--out", default="outputs/demo")
    ui = commands.add_parser("ui", help="Open the local browser interface (requires [ui] extra)")
    ui.add_argument("--port", type=int, default=8501)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            with Path(args.path).open("x", encoding="utf-8") as f:
                json.dump(demo_config(), f, indent=2, allow_nan=False)
                f.write("\n")
            print(f"Created {Path(args.path).resolve()}. Edit forecast assumptions before running.")
        elif args.command == "validate":
            from .engine import earnings_grid
            c = load_config(args.config)
            earnings_grid(c)
            print("Valid scenario. Source URLs are assertions; validation does not verify custom facts.")
        elif args.command == "run":
            from .engine import run_model
            from .report import export_result
            from .selector import compute_smart_selector
            result = run_model(load_config(args.config) if args.config else demo_config())
            selector = compute_smart_selector(result)
            directory = export_result(result, selector, args.out)
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
