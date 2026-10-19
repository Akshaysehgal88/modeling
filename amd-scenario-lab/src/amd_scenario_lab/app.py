"""Local browser interface, loaded through `amd-lab ui`."""
import json

import pandas as pd
import streamlit as st

from amd_scenario_lab.config import NOTICE, demo_config, public_facts, validate_config
from amd_scenario_lab.engine import run_model
from amd_scenario_lab.report import audit_record, chart_plotly, html_report, output_table
from amd_scenario_lab.selector import compute_smart_selector

st.set_page_config(page_title="AMD Scenario Lab", page_icon="📈", layout="wide")
st.title("AMD Scenario Lab")
st.write("Explore how earnings, valuation and hypothetical market conditions change a shared scenario distribution.")
st.warning(NOTICE)

with st.sidebar:
    st.header("Start a scenario")
    st.caption("Runs on your computer. No market-data account or API key needed.")
    uploaded = st.file_uploader("Load a scenario JSON (optional)", type=["json"])
    config = demo_config()
    if uploaded is not None:
        try:
            config = validate_config(json.loads(uploaded.getvalue()))
        except (ValueError, TypeError, KeyError) as exc:
            st.error(f"Invalid scenario: {exc}")
            st.stop()
    with st.form("scenario_controls"):
        start = st.text_input("Starting month (YYYY-MM)", config["start_month"])
        horizon = st.number_input("Forecast months", 1, 60, config["horizon_months"])
        paths = st.number_input("Simulation paths", 100, 20000, config["n_paths"], step=100)
        seed = st.number_input("Simulation seed", 0, 2**32 - 1, config["seed"])
        st.subheader("Price anchor")
        kinds = ["synthetic_demo", "public_observation", "user_assumption"]
        kind = st.selectbox("Anchor classification", kinds, index=kinds.index(config["anchor"]["classification"]))
        price = st.number_input("Starting price (USD/share)", .01, 100000., float(config["anchor"]["price"]))
        as_of = st.text_input("Anchor date (YYYY-MM-DD)", config["anchor"]["as_of"])
        url = st.text_input("Public quote source URL", config["anchor"]["source_url"])
        note = st.text_input("Anchor note", config["anchor"]["note"])
        st.subheader("Forecast assumptions")
        annual_facts = [f for f in public_facts()["facts"] if f["period_type"] == "annual"]
        ids = [f["id"] for f in annual_facts]
        base_id = st.selectbox("Disclosed annual EPS base", ids, index=ids.index(config["earnings"]["base_fact_id"]),
                               format_func=lambda x: next(f"{f['period']} {f['basis']}: ${f['value']:.2f}" for f in annual_facts if f["id"] == x))
        growth = {}
        for key in ("slowdown", "reference", "acceleration"):
            growth[key] = st.number_input(f"{key.title()} annual EPS growth (%)", -80., 200., float(config["earnings"]["annual_growth"][key] * 100)) / 100
        pe = st.number_input("Long-run forward P/E assumption", .1, 200., float(config["market"]["terminal_pe"]))
        volatility = st.slider("Monthly log-price innovation scale (assumed)", 0., 1., float(config["market"]["monthly_volatility"]), .01)
        method = st.selectbox("Adaptive overlay method", ["conditioned", "path_rank"], index=["conditioned", "path_rank"].index(config["selector"]["method"]))
        selector_seed = st.number_input("Overlay seed (hypothetical conditions)", 0, 2**32 - 1, config["selector"]["seed"])
        submitted = st.form_submit_button("Run scenario", type="primary")

with st.expander("What is disclosed, and what is assumed?", expanded=True):
    st.markdown("**Disclosed:** the historical EPS facts below, with dated issuer sources. **Forecast assumptions:** future earnings growth, P/E, weights, volatility, event timing/outcomes, credit and regime dynamics. **Model outputs:** every future price, percentile and adaptive overlay.")
    st.caption("The bundled $100 anchor is synthetic. This is a frozen public-source reference reviewed on 19 October 2026, not a live market view. Custom source URLs are not independently verified by the app.")

if submitted:
    config.update(start_month=start, horizon_months=int(horizon), n_paths=int(paths), seed=int(seed))
    config["anchor"] = dict(price=price, classification=kind, as_of=as_of, source_url=url, note=note)
    config["earnings"].update(base_fact_id=base_id, annual_growth=growth)
    config["market"].update(terminal_pe=pe, monthly_volatility=volatility)
    config["selector"].update(method=method, seed=int(selector_seed))
    try:
        with st.spinner("Simulating forecast scenarios..."):
            result = run_model(config)
            selector = compute_smart_selector(result)
        st.session_state["run"] = (result, selector)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(str(exc))

if "run" in st.session_state:
    result, selector = st.session_state["run"]
    c = result["config"]
    st.info(f"Displayed run: {c['start_month']} + {c['horizon_months']} months | {c['n_paths']:,} paths | seed {c['seed']} | {c['anchor']['classification']} anchor ${c['anchor']['price']:.2f} ({c['anchor']['as_of']}).")
    st.caption("Press Run scenario after changing controls to refresh the displayed run.")
    st.plotly_chart(chart_plotly(result, selector), use_container_width=True)
    st.caption("P10-P90 describes model outcomes only. The conditioned overlay uses a randomly sampled hypothetical market history, not known future conditions. It can jump between months; it is not one coherent traded-price path.")
    tabs = st.tabs(["Monthly outputs", "Overlay diagnostics", "Assumptions & downloads"])
    with tabs[0]:
        st.dataframe(output_table(result, selector), use_container_width=True, hide_index=True)
    with tabs[1]:
        st.dataframe(selector, use_container_width=True, hide_index=True)
        st.caption("Effective sample size measures kernel support inside this simulation. It is not empirical confidence. path_rank preserves a sampled price trajectory only where P10-P90 clipping does not alter it.")
    with tabs[2]:
        st.json(c, expanded=False)
        st.caption("Downloads include your configuration and notes. Review custom inputs before sharing them.")
        st.download_button("Download scenario JSON", json.dumps(c, indent=2), "scenario.json", "application/json")
        st.download_button("Download monthly CSV", output_table(result, selector).to_csv(index=False), "monthly.csv", "text/csv")
        diagnostic_export = selector.copy()
        diagnostic_export["classification"] = "forecast_model_output"
        diagnostic_export.loc[0, "classification"] = c["anchor"]["classification"]
        diagnostic_export["notice"] = NOTICE
        st.download_button("Download diagnostics CSV", diagnostic_export.to_csv(index=False), "selector.csv", "text/csv")
        st.download_button("Download standalone HTML report", html_report(result, selector), "report.html", "text/html")
        st.download_button("Download provenance & audit JSON", json.dumps(audit_record(result, selector), indent=2), "audit.json", "application/json")
else:
    st.info("Choose assumptions in the sidebar and press Run scenario. The demo is ready to run.")

with st.expander("Public fact register"):
    st.dataframe(pd.DataFrame(public_facts()["facts"]), use_container_width=True, hide_index=True)
    for f in public_facts()["facts"]:
        st.markdown(f"[{f['period']} {f['basis']} EPS disclosure]({f['source_url']}) - published {f['published_on']}")
