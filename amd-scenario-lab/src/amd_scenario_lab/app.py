"""Browser controls around the preserved original AMD model."""
from copy import deepcopy
from hashlib import sha256
import json

import pandas as pd
import streamlit as st

from amd_scenario_lab.config import NOTICE, demo_config, public_facts, validate_config
from amd_scenario_lab.engine import run_model
from amd_scenario_lab.report import audit_record, chart_plotly, html_report, output_table
from amd_scenario_lab.selector import compute_smart_selector, MARKET_OPTIONS

st.set_page_config(page_title="AMD Scenario Lab", page_icon="📈", layout="wide")
st.title("AMD Scenario Lab")
st.caption("Original v3 model: earnings, evidence, credit, regimes and adaptive monthly selection.")
st.caption(NOTICE)

with st.sidebar:
    st.header("Scenario")
    uploaded = st.file_uploader("Load demo / scenario JSON", type=["json"])
    regime_upload = st.file_uploader("Load monthly regime CSV (optional)", type=["csv"])
    st.markdown("**Original snapshot:** October 2026 through October 2028.")
    st.caption("The original anchor, annual EPS curves, monthly events, paired-return calibration and seeds are retained. No personal finance inputs are included.")

try:
    raw = uploaded.getvalue() if uploaded else json.dumps(demo_config()).encode()
    imported = validate_config(json.loads(raw))
    if regime_upload:
        rows = pd.read_csv(regime_upload).fillna("")
        if "notes" not in rows:
            rows["notes"] = ""
        if len(rows) == 24:
            rows = pd.concat([pd.DataFrame([demo_config()["monthly_overrides"][0]]), rows], ignore_index=True)
        imported["monthly_overrides"] = rows.to_dict("records")
        validate_config(imported)
        raw += regime_upload.getvalue()
except (ValueError, TypeError, KeyError) as exc:
    st.error(f"Invalid scenario input: {exc}")
    st.stop()

identity = sha256(raw).hexdigest()
if st.session_state.get("input_identity") != identity:
    st.session_state["input_identity"] = identity
    st.session_state["scenario"] = imported
    st.session_state.pop("run", None)
config = deepcopy(st.session_state["scenario"])

with st.form("scenario_controls"):
    st.subheader("Starting conditions and annual EPS assumptions")
    a, b, d = st.columns(3)
    with a:
        price = st.number_input("Starting price (USD/share)", 1.01, 19999., float(config["anchor"]["price"]))
        paths = st.number_input("Simulation paths", 100, 50000, int(config["n_paths"]), step=100)
        seed = st.number_input("Simulation seed", 0, 2**32-1, int(config["seed"]))
    with b:
        regimes = [-2, -1, 0, 1, 2]
        initial = st.selectbox("Initial market regime", regimes,
                               index=regimes.index(config["settings"]["initial_regime"]),
                               format_func=lambda x: MARKET_OPTIONS[x+3])
        stress = st.number_input("Initial credit stress", 0., 2., float(config["settings"]["initial_credit_stress"]), step=.05)
        method = st.selectbox("Adaptive overlay method", ["conditioned", "path_rank"],
                              index=["conditioned", "path_rank"].index(config["selector"]["method"]))
    with d:
        eps = {}
        for year in range(26, 31):
            eps[f"eps{year}"] = st.number_input(f"FY20{year} adjusted EPS", .001, 1000., float(config["settings"][f"eps{year}"]), step=.1)

    with st.expander("All market, evidence and selector assumptions"):
        st.caption("The original settings are kept. Editing the selector changes the overlay; it does not resimulate or force market states in the underlying distribution.")
        settings = deepcopy(config["settings"])
        columns = st.columns(3)
        for i, (key, value) in enumerate(settings.items()):
            if key in eps or key in ("initial_regime", "initial_credit_stress"):
                continue
            with columns[i % 3]:
                settings[key] = st.number_input(key.replace("_", " ").title(), value=float(value), key=f"setting_{key}_{identity}")
        selector = deepcopy(config["selector"])
        selector["method"] = method
        selector["selector_seed"] = st.number_input("Overlay seed", 0, 2**32-1, int(selector["selector_seed"]))
        fixed = st.checkbox("Choose selector path index", value=selector["path_index"] is not None)
        path_index = st.number_input("Selector path index", 0, 49999, int(selector["path_index"] or 0))
        selector["path_index"] = int(path_index) if fixed else None
        for key in ("condition_strength", "psyche_strength", "low_percentile", "high_percentile"):
            selector[key] = st.number_input(key.replace("_", " ").title(), value=float(selector[key]), key=f"selector_{key}_{identity}")
        selector["min_conditional_paths"] = st.number_input("Minimum conditional paths", 1, 50000, int(selector["min_conditional_paths"]))
        st.caption("Anchor classification and source notes are saved in the scenario; they do not alter the numerical model.")
        kinds = ["user_supplied_snapshot", "public_observation", "user_assumption", "synthetic_demo"]
        anchor_kind = st.selectbox("Anchor classification", kinds, index=kinds.index(config["anchor"]["classification"]))
        anchor_date = st.text_input("Anchor date", config["anchor"]["as_of"])
        anchor_url = st.text_input("Anchor source URL", config["anchor"]["source_url"])
        anchor_note = st.text_input("Anchor note", config["anchor"]["note"])

    with st.expander("Scenario curves, priors and regime premiums"):
        st.caption("EPS templates define slowdown/acceleration ratios around the editable annual reference EPS above. This is the original spread behavior. Priors and premiums are subjective model assumptions.")
        curve_rows = [{"scenario": name, "prior": config["priors"][i], **config["scenario_eps"][name]}
                      for i, name in enumerate(("slowdown", "reference", "acceleration"))]
        curves = st.data_editor(pd.DataFrame(curve_rows), key=f"curves_{identity}", hide_index=True,
                                disabled=["scenario"], num_rows="fixed", use_container_width=True)
        premiums = st.data_editor(pd.DataFrame({"regime": MARKET_OPTIONS[1:], "log_premium": config["regime_log_premiums"]}),
                                  key=f"premiums_{identity}", disabled=["regime"], hide_index=True, num_rows="fixed")

    with st.expander("Monthly evidence and event assumptions"):
        st.caption("The original 24 evidence windows and likelihoods are retained. Event narratives and timing notes are scenario assumptions, including wording from the original inputs; they are not independently verified announcements. Positive/negative force a what-if outcome; neutral supplies no new evidence.")
        event_frame = pd.DataFrame(config["events"]).drop(columns="classification")
        event_edit = st.data_editor(event_frame, key=f"events_{identity}", hide_index=True, num_rows="fixed",
            use_container_width=True, disabled=["month"], column_config={
                "status": st.column_config.SelectboxColumn("Outcome / what-if", options=["pending", "positive", "negative", "neutral"]),
                "prob_positive": st.column_config.NumberColumn("Positive likelihood", min_value=0., max_value=1., step=.01),
                "revelation_chance": st.column_config.NumberColumn("Evidence arrival", min_value=0., max_value=1., step=.01),
                "materiality": st.column_config.NumberColumn("Materiality", min_value=0., max_value=3., step=.1)})

    st.subheader("Month-by-month market regime selector")
    st.caption("Choose Auto or a regime for each month. Set a percentile from 10 to 90 to override that month's selection; 0 uses the automatic/regime selection. A forced percentile takes precedence over a regime. The initial anchor stays fixed. These choices affect only the magenta overlay.")
    controls = pd.DataFrame(config["monthly_overrides"])
    edited = st.data_editor(controls.iloc[1:].reset_index(drop=True), key=f"monthly_regimes_{identity}",
        hide_index=True, use_container_width=True, num_rows="fixed", disabled=["month"], column_config={
            "market_condition": st.column_config.SelectboxColumn("Market regime", options=MARKET_OPTIONS, required=True),
            "manual_percentile": st.column_config.NumberColumn("Percentile (0 = auto)", min_value=0., max_value=90., step=5.),
            "notes": st.column_config.TextColumn("Scenario notes")})
    submitted = st.form_submit_button("Run scenario", type="primary")

if submitted:
    candidate = deepcopy(config)
    candidate["anchor"].update(price=price, classification=anchor_kind, as_of=anchor_date, source_url=anchor_url, note=anchor_note)
    candidate.update(n_paths=int(paths), seed=int(seed))
    candidate["settings"] = dict(settings, **eps)
    candidate["settings"].update(initial_regime=int(initial), initial_credit_stress=stress)
    candidate["selector"] = selector
    candidate["scenario_eps"] = {row["scenario"]: {str(y): float(row[str(y)]) for y in range(2026, 2031)} for row in curves.to_dict("records")}
    candidate["priors"] = curves["prior"].astype(float).tolist()
    candidate["regime_log_premiums"] = premiums.log_premium.astype(float).tolist()
    candidate["events"] = [dict(row, classification="forecast_assumption") for row in event_edit.to_dict("records")]
    candidate["monthly_overrides"] = [controls.iloc[0].to_dict(), *edited.to_dict("records")]
    try:
        with st.spinner("Running the original model and monthly selector..."):
            result = run_model(candidate)
            overlay = compute_smart_selector(result)
        st.session_state["scenario"] = candidate
        st.session_state["run"] = (result, overlay)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"Scenario not applied: {exc}")

if "run" not in st.session_state:
    try:
        result = run_model(config)
        st.session_state["run"] = (result, compute_smart_selector(result))
    except (ValueError, TypeError, KeyError) as exc:
        st.error(str(exc))
        st.stop()

result, overlay = st.session_state["run"]
c = result["config"]
st.info(f"Displayed run: {c['n_paths']:,} paths | seed {c['seed']} | selector seed {c['selector']['selector_seed']} | {c['anchor']['classification']} anchor ${c['anchor']['price']:.2f}. Press Run scenario to apply edits.")
st.plotly_chart(chart_plotly(result, overlay), use_container_width=True)
st.caption("The blue reference, green P50, amber P80 and magenta adaptive overlay use the original model. Quantile curves and conditional monthly selections need not form a single trading path.")

output_tabs = st.tabs(["Monthly outputs", "Selector diagnostics", "Configuration & downloads"])
with output_tabs[0]:
    st.dataframe(output_table(result, overlay), hide_index=True, use_container_width=True)
with output_tabs[1]:
    st.dataframe(overlay, hide_index=True, use_container_width=True)
    st.caption("A rare manually requested regime can have too few matching paths. The tool reports this instead of substituting another regime. Increase paths or change that month's selection.")
with output_tabs[2]:
    st.json(c, expanded=False)
    st.download_button("Download scenario JSON", json.dumps(c, indent=2), "scenario.json", "application/json")
    st.download_button("Download monthly regime CSV", pd.DataFrame(c["monthly_overrides"]).to_csv(index=False), "monthly_overrides.csv", "text/csv")
    st.download_button("Download monthly CSV", output_table(result, overlay).to_csv(index=False), "monthly.csv", "text/csv")
    diagnostics = overlay.copy()
    diagnostics["classification"] = "forecast_model_output"
    diagnostics.loc[0, "classification"] = c["anchor"]["classification"]
    diagnostics["notice"] = NOTICE
    st.download_button("Download diagnostics CSV", diagnostics.to_csv(index=False), "selector.csv", "text/csv")
    st.download_button("Download standalone HTML report", html_report(result, overlay), "report.html", "text/html")
    st.download_button("Download provenance & audit JSON", json.dumps(audit_record(result, overlay), indent=2), "audit.json", "application/json")
with st.expander("Input provenance"):
    st.write("Original annual earnings curves, evidence windows, priors, calibration sample and selector settings are bundled. They retain their role as model inputs. The historical EPS disclosures below are background references; they do not overwrite the scenario assumptions.")
    st.json(result["meta"], expanded=False)
    st.dataframe(pd.DataFrame(public_facts()["facts"]), hide_index=True, use_container_width=True)
