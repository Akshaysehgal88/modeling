"""Browser controls around the preserved original AMD model."""
from copy import deepcopy
from hashlib import sha256
import json
import math

import pandas as pd
import streamlit as st

from scenario_lab.config import NOTICE, demo_config, public_facts, validate_config
from scenario_lab.engine import run_model
from scenario_lab.report import audit_record, chart_plotly, html_report, output_table
from scenario_lab.selector import compute_smart_selector, MARKET_OPTIONS
from scenario_lab.catalog import list_companies, get_company, company_info
from scenario_lab.currency import SYMBOLS, fx_snapshot, reference_rate, for_display


def input_error(exc):
    """Translate validation details into the labels shown in this form."""
    message = str(exc)
    if "priors must sum" in message:
        return "Starting weights must total 100%."
    if "Need percentile limits spanning" in message:
        return "The magenta line's lowest percentile must be above 0 and below 50; its highest must be above 50 and below 100."
    if "Forced percentiles must be inside" in message:
        return "A monthly percentile is outside the magenta line's limits. Adjust that month or change the limits in Advanced: magenta line."
    if "nonpositive" in message and "EPS" in message:
        return "The alternative earnings cases produce zero or negative EPS. Reduce the percentage differences or the Case spread multiplier."
    labels = {"n_paths": "Number of simulated paths", "selector_seed": "Magenta line random seed",
        "path_index": "Simulated path number", "min_conditional_paths": "Minimum matching paths",
        "condition_strength": "Market matching strength", "psyche_strength": "Market mood matching weight",
        "low_percentile": "Lowest allowed percentile (stored as a fraction)",
        "high_percentile": "Highest allowed percentile (stored as a fraction)",
        "manual_percentile": "Monthly percentile", "market_condition": "Monthly market condition",
        "prob_positive": "Chance of positive news", "revelation_chance": "Chance news arrives",
        "materiality": "Event impact", "anchor.as_of": "Starting price date", "anchor.price": "Starting price",
        "anchor.source_url": "Starting price source URL", "initial_regime": "Starting market condition",
        "initial_credit_stress": "Starting funding stress"}
    for _, _, fields in globals().get("groups", []):
        labels.update({key: label for key, label, _ in fields})
    for field, label in sorted(labels.items(), key=lambda item: -len(item[0])):
        message = message.replace(field, label)
    return message

st.set_page_config(page_title="Scenario Lab", page_icon="\U0001f4c8", layout="wide")
st.title("Scenario Lab")
st.caption("Choose a company, review its earnings assumptions, then adjust the monthly market conditions if needed.")
st.caption("Demos use dated inputs and editable forecast assumptions. They are not live prices or company guidance.")

company_column, currency_column = st.columns([2, 1])
with company_column:
    ids = [entry["id"] for entry in list_companies()]
    selected_company = st.selectbox("Company", ids, key="selected_company",
        format_func=lambda id: f"{get_company(id)['name']} ({get_company(id)['symbol']} · {get_company(id)['currency']})")
company = get_company(selected_company)
native_currency = company["currency"]
with currency_column:
    currencies = [native_currency, *[c for c in SYMBOLS if c != native_currency]]
    display_currency = st.selectbox("Display currency", currencies, key=f"display_currency_{selected_company}",
        help="Changes the currency of results only. All inputs below stay in the company's listing currency.")
    display_rate = 1.
    if display_currency != native_currency:
        display_rate = st.number_input(f"{display_currency} per 1 {native_currency}", min_value=.000000001,
            value=reference_rate(native_currency, display_currency), format="%.9f",
            key=f"fx_{selected_company}_{display_currency}",
            help="A fixed conversion for the whole chart. Edit this rate to use your own exchange-rate assumption.")
        st.caption(f"Exchange-rate snapshot: {fx_snapshot()['as_of']}. Inputs below remain in {native_currency}.")

with st.sidebar:
    st.header("Load a saved scenario")
    st.caption("The selected company's demo loads automatically. Upload a file only to replace it.")
    uploaded = st.file_uploader("Scenario JSON (optional)", type=["json"], key=f"scenario_upload_{selected_company}")
    regime_upload = st.file_uploader("Monthly market choices CSV (optional)", type=["csv"], key=f"regime_upload_{selected_company}")
    st.markdown("**Chart period:** October 2026 to October 2028.")
    st.caption("If you upload both files, the CSV replaces the monthly choices in the JSON.")
    if selected_company == "AMD":
        st.caption("AMD loads the original model and assumptions. The original numerical behavior is preserved.")
    else:
        st.caption(f"{company['name']} · {company['exchange']} · {native_currency} per {company['unit'].replace('_', ' ')}. EPS basis: {company['eps_basis']}. Inputs use this listing and earnings basis.")

try:
    raw = uploaded.getvalue() if uploaded else json.dumps(demo_config(selected_company)).encode()
    imported = validate_config(json.loads(raw))
    if company_info(imported)["id"] != selected_company:
        raise ValueError(f"This JSON belongs to {company_info(imported)['name']}; select that company before loading it")
    if regime_upload:
        rows = pd.read_csv(regime_upload).fillna("")
        if "notes" not in rows:
            rows["notes"] = ""
        if len(rows) == 24:
            rows = pd.concat([pd.DataFrame([demo_config(selected_company)["monthly_overrides"][0]]), rows], ignore_index=True)
        imported["monthly_overrides"] = rows.to_dict("records")
        validate_config(imported)
        raw += regime_upload.getvalue()
except (ValueError, TypeError, KeyError) as exc:
    st.error(f"Could not load scenario: {input_error(exc)}")
    st.stop()

identity = sha256(raw).hexdigest()
workspaces = st.session_state.setdefault("company_workspaces", {})
if selected_company not in workspaces or workspaces[selected_company]["input_identity"] != identity:
    workspaces[selected_company] = {"input_identity": identity, "scenario": imported}
workspace = workspaces[selected_company]
config = deepcopy(workspace["scenario"])

with st.form(f"scenario_controls_{selected_company}"):
    st.subheader("Starting point and earnings forecast")
    st.caption(f"All amounts here are in {native_currency}, even when the chart uses another display currency. "
               "The demo is ready to run; change only the assumptions you want to explore.")
    settings = deepcopy(config["settings"])
    selector = deepcopy(config["selector"])
    a, b = st.columns(2)
    with a:
        price = st.number_input(f"Starting price ({native_currency}/share)",
            1.01 if selected_company == "AMD" else .0001,
            19999. if selected_company == "AMD" else 1e9, float(config["anchor"]["price"]),
            help="The price where every simulated path begins. Its date and source are under Starting price source.")
        regimes = [-2, -1, 0, 1, 2]
        initial = st.selectbox("Starting market condition", regimes,
            index=regimes.index(settings["initial_regime"]), format_func=lambda x: MARKET_OPTIONS[x+3],
            help="The market mood at the start of all simulations. Monthly choices below affect only the magenta line.")
        stress = st.number_input("Starting funding stress (0–2)", 0., 2.,
            float(settings["initial_credit_stress"]), step=.05,
            help="Model index: 0 means little funding pressure; 2 means high pressure. This is not an interest rate or a percentage.")
    with b:
        st.markdown("**Base earnings per share (EPS)**")
        st.caption("Your annual earnings forecast. The alternative cases below are measured relative to these values. "
                   "FY means fiscal year. The model spreads annual forecasts over calendar months.")
        eps = {}
        for year in range(26, 31):
            eps[f"eps{year}"] = st.number_input(f"FY20{year} adjusted EPS" if selected_company == "AMD" else f"FY20{year} EPS ({native_currency})",
                .001 if selected_company == "AMD" else .000001, 1000. if selected_company == "AMD" else 1e9,
                float(settings[f"eps{year}"]), step=.1,
                help=f"{native_currency} per listed share or unit. Earnings basis: {company['eps_basis']}. "
                     "Later years also affect how far ahead the model values earnings.")

    with st.expander("Alternative earnings cases and starting weights"):
        st.caption("Slowdown and acceleration are percentage differences from your base EPS, not a second earnings forecast. "
                   "For example, −20 means 20% below base EPS. The base case has no difference. "
                   "The case spread multiplier in Advanced: valuation and earnings scales these differences.")
        case_rows = [{"scenario": name, **{str(y): 100 * (config["scenario_eps"][name][str(y)] /
                     config["scenario_eps"]["reference"][str(y)] - 1) for y in range(2026, 2031)}}
                     for name in ("slowdown", "acceleration")]
        case_edit = st.data_editor(pd.DataFrame(case_rows), key=f"curves_{identity}", hide_index=True,
            disabled=["scenario"], num_rows="fixed", use_container_width=True, column_config={
                "scenario": st.column_config.TextColumn("Earnings case"),
                **{str(y): st.column_config.NumberColumn(f"FY{y} difference (%)", format="%.2f", required=True,
                    help="Percentage above or below the base EPS. Negative values mean lower earnings.") for y in range(2026, 2031)}})
        weights = st.data_editor(pd.DataFrame({"scenario": ["Slowdown", "Base", "Acceleration"],
            "weight": [p * 100 for p in config["priors"]]}), key=f"weights_{identity}",
            disabled=["scenario"], hide_index=True, num_rows="fixed", column_config={
                "scenario": st.column_config.TextColumn("Earnings case"),
                "weight": st.column_config.NumberColumn("Starting weight (%)", min_value=0., max_value=100., required=True,
                    help="The three weights must total 100%. These are assumptions, not measured market probabilities.")})
        st.caption("All three starting weights must be above zero and total 100%. Monthly evidence can shift them as the simulation runs.")

    with st.expander("Monthly business events and outcomes"):
        st.caption("Each row is a forecast assumption about a business event. Pending lets the model simulate whether news arrives "
                   "and whether it is positive. Positive or negative forces that outcome in every path; neutral supplies no new evidence. "
                   "Positive and negative outcomes bypass the news-arrival chance; the positive-news likelihood still affects how surprising the news is. These choices affect the full simulation.")
        st.caption("Chances use 0 to 1: 0.6 means 60%. Impact uses 0 to 3: 0 means no event impact. "
                   "Descriptions and dates are scenario notes, not verified announcements.")
        event_frame = pd.DataFrame(config["events"]).drop(columns="classification")
        event_edit = st.data_editor(event_frame, key=f"events_{identity}", hide_index=True, num_rows="fixed",
            use_container_width=True, disabled=["month"], column_config={
                "month": st.column_config.TextColumn("Month"),
                "catalyst": st.column_config.TextColumn("Business event"),
                "upside_evidence": st.column_config.TextColumn("What would be positive"),
                "downside_evidence": st.column_config.TextColumn("What would be negative"),
                "timing": st.column_config.TextColumn("Timing notes"),
                "status": st.column_config.SelectboxColumn("Outcome", options=["pending", "positive", "negative", "neutral"], required=True),
                "prob_positive": st.column_config.NumberColumn("Chance of positive news (0–1)", min_value=0., max_value=1., step=.01, required=True,
                    help="Base likelihood before the model adjusts it for the earnings case. Simulates pending news and weights positive or negative evidence."),
                "revelation_chance": st.column_config.NumberColumn("Chance news arrives (0–1)", min_value=0., max_value=1., step=.01, required=True,
                    help="Chance this month's event supplies evidence. Used for pending outcomes."),
                "materiality": st.column_config.NumberColumn("Event impact (0–3)", min_value=0., max_value=3., step=.1, required=True,
                    help="Scales how strongly the event distinguishes earnings cases and changes funding stress.")})

    st.subheader("Month-by-month market regime selector")
    st.caption("These choices change only the magenta line; they do not change the simulated price range. "
               "Auto follows the selected method. Choose a market condition to explore a different month, "
               "or enter a percentile to override that condition. Leave the percentile blank to use Auto or the chosen condition.")
    st.caption("A percentile is a position in that month's price range: 50 is the median; 80 is higher than 80% of modeled prices. "
               "It is not a price growth rate or a forecast confidence level. The starting price stays fixed.")
    controls = pd.DataFrame(config["monthly_overrides"])
    monthly_input = controls.iloc[1:].reset_index(drop=True).copy()
    monthly_input["manual_percentile"] = monthly_input.manual_percentile.replace(0, float("nan"))
    edited = st.data_editor(monthly_input, key=f"monthly_regimes_{identity}",
        hide_index=True, use_container_width=True, num_rows="fixed", disabled=["month"], column_config={
            "month": st.column_config.TextColumn("Month"),
            "market_condition": st.column_config.SelectboxColumn("Market condition", options=MARKET_OPTIONS, required=True),
            "manual_percentile": st.column_config.NumberColumn("Percentile (blank = use condition)", min_value=10., max_value=90., step=5.,
                help="Optional 10–90. Takes priority over the market condition and must be within the magenta line's limits in Advanced: magenta line."),
            "notes": st.column_config.TextColumn("Your notes")})

    st.markdown("**Advanced settings — optional**")
    st.caption("The demo already supplies these values. Open a section only if you want to change how the model works.")
    groups = [
        ("Advanced: valuation and earnings", "These settings affect the full simulation and the blue earnings reference.", [
            ("stabilized_forward_pe", "Long-term forward P/E", "The price-to-earnings multiple the reference valuation gradually approaches."),
            ("pe_normalization_months", "P/E adjustment time (months)", "Time scale for moving toward the long-term P/E. Larger values make adjustment slower; it is not a deadline."),
            ("initial_lookthrough_weight", "Starting weight on later earnings (0–0.5)", "Share of the starting earnings estimate taken from the following year's forward earnings. 0.16 means 16%; this can change with market mood."),
            ("earnings_scenario_spread", "Case spread multiplier", "1 keeps the slowdown/acceleration differences above. 0 makes earnings identical across cases; 2 doubles the differences."),
            ("evidence_strength", "Overall event impact multiplier", "Multiplies every monthly event's impact. 1 keeps the row values; 0 removes their effect on funding stress and earnings-case updates."),
            ("scenario_discrimination", "How strongly news distinguishes earnings cases", "Larger values make positive news more likely in acceleration and less likely in slowdown. 0 stops news from shifting earnings-case weights.")]),
        ("Advanced: funding conditions", "Funding stress is an index from 0 to 2. These settings control its changes and price effect.", [
            ("credit_persistence", "Funding stress persistence (0.25–1)", "Fraction of last month's stress carried forward. Higher values make funding conditions change more slowly."),
            ("credit_long_run", "Long-term funding stress (0–2)", "The stress level the model tends toward before news and random monthly changes."),
            ("credit_monthly_noise", "Monthly funding stress variation", "Size of random monthly changes in the stress index. 0 removes this random component."),
            ("credit_price_sensitivity", "Price sensitivity to funding stress", "Larger values cause a larger price decline when funding stress rises from its starting level.")]),
        ("Advanced: price swings and market mood", "These settings affect the full simulation. Market swings and company-specific swings are separate sources of variation.", [
            ("peer_shock_scale", "Peer-market price swing multiplier", "1 uses the historical peer-market swings at their calibrated size; 0 removes them. Peer swings also influence market-condition changes."),
            ("idio_shock_scale", "Company-specific price swing multiplier", "Scales the historical company price variation left after allowing for peer-market moves. 0 removes this component."),
            ("switching_tendency", "Market condition change frequency", "Larger values make changes between market conditions more frequent. 0 keeps the starting condition throughout."),
            ("sentiment_persistence", "Market mood persistence (0–0.999)", "Fraction of the previous month's unexplained price effect retained next month. Higher values let it last longer."),
            ("momentum_feedback", "Recent price trend influence", "How strongly recent price trends feed back into prices. Optimistic and pessimistic multipliers below scale this effect."),
            ("optimism_feedback", "Trend multiplier in optimistic markets", "Scales recent price trend influence when the market condition is optimistic or euphoric."),
            ("pessimism_feedback", "Trend multiplier in pessimistic markets", "Scales recent price trend influence when the market condition is risk-off or severe panic.")])]
    for title, explanation, fields in groups:
        with st.expander(title):
            st.caption(explanation)
            columns = st.columns(2)
            for i, (key, label, help_text) in enumerate(fields):
                with columns[i % 2]:
                    settings[key] = st.number_input(label, value=float(settings[key]),
                        key=f"setting_{key}_{identity}", help=help_text)

    with st.expander("Advanced: market condition price adjustments"):
        st.caption("Price adjustments for each market condition, shown as percentages. For example, −10 means a 10% discount. "
                   "Only changes from the starting condition affect prices; an unchanged condition adds no repeated discount or premium. "
                   "Saved JSON keeps the original log-unit values.")
        premium_percentages = [100 * math.expm1(value) for value in config["regime_log_premiums"]]
        premiums = st.data_editor(pd.DataFrame({"regime": MARKET_OPTIONS[1:], "adjustment_percent": premium_percentages}),
            key=f"premiums_{identity}", disabled=["regime"], hide_index=True, num_rows="fixed", column_config={
                "regime": st.column_config.TextColumn("Market condition"),
                "adjustment_percent": st.column_config.NumberColumn("Price adjustment (%)", format="%.2f", required=True,
                    min_value=100 * math.expm1(-2), max_value=100 * math.expm1(2))})

    with st.expander("Advanced: magenta line"):
        st.caption("These controls affect only the magenta line. The simulated price range stays unchanged.")
        method = st.selectbox("Automatic line method", ["conditioned", "path_rank"],
            index=["conditioned", "path_rank"].index(selector["method"]),
            format_func=lambda x: {"conditioned": "Match similar market conditions", "path_rank": "Follow one simulated price path"}[x],
            help="Matching uses each month's prices under similar market conditions, funding stress and earnings beliefs. "
                 "The alternative follows one simulated path. Monthly choices take priority over either method.")
        selector["method"] = method
        st.caption("Matching selects prices separately each month, so its line may not be one continuous simulated path.")
        columns = st.columns(2)
        for i, (key, label, help_text) in enumerate([
            ("condition_strength", "Market matching strength", "Larger values favor paths with funding stress and earnings beliefs closer to the sampled market history. 0 matches only market condition."),
            ("psyche_strength", "Market mood matching weight", "Adds similarity in unexplained price sentiment to the match. 0 ignores sentiment; market matching strength scales the whole match.")]):
            with columns[i]:
                selector[key] = st.number_input(label, value=float(selector[key]), key=f"selector_{key}_{identity}", help=help_text)
        st.caption("Matching settings apply to the matching method and to months with a manually chosen market condition. "
                   "They are unused when following a path or setting a percentile directly.")
        lower = st.number_input("Lowest allowed percentile (%)", 0., 50., float(selector["low_percentile"] * 100),
            help="Must be above 0 and below 50. Monthly percentiles must also be between 10 and 90.")
        upper = st.number_input("Highest allowed percentile (%)", 50., 100., float(selector["high_percentile"] * 100),
            help="Must be above 50 and below 100. These limits do not change the chart's gray P10–P90 band.")
        # Keep untouched values exactly, including custom JSON values.
        if lower != selector["low_percentile"] * 100:
            selector["low_percentile"] = lower / 100
        if upper != selector["high_percentile"] * 100:
            selector["high_percentile"] = upper / 100
        selector["min_conditional_paths"] = st.number_input("Minimum matching paths", 1, 50000, int(selector["min_conditional_paths"]),
            help="Rejects a manually chosen condition if fewer paths support it. Raise Number of simulated paths or choose another condition if needed.")

    with st.expander("Advanced: simulation size and repeatability"):
        paths = st.number_input("Number of simulated paths", 100, 50000, int(config["n_paths"]), step=100,
            help="More paths give a larger sample and take longer to run. This does not change the economic assumptions.")
        seed = st.number_input("Simulation random seed", 0, 2**32-1, int(config["seed"]),
            help="A repeatability code, not a forecast assumption. The same complete inputs and seed reproduce the price distribution.")
        selector["selector_seed"] = st.number_input("Magenta line random seed", 0, 2**32-1, int(selector["selector_seed"]),
            help="Chooses a simulated market history for the magenta line. Changing this leaves the price distribution unchanged. Ignored when a fixed path is chosen.")
        fixed = st.checkbox("Use a specific simulated path", value=selector["path_index"] is not None,
            help="Advanced repeatability option for the magenta line. Leave off to let its random seed choose a path.")
        path_index = st.number_input("Simulated path number (starts at 0)", 0, 49999, int(selector["path_index"] or 0),
            disabled=not fixed, help="Must be smaller than Number of simulated paths. Used only when the checkbox is on.")
        selector["path_index"] = int(path_index) if fixed else None

    with st.expander("Starting price source"):
        st.caption("Describes where the starting price came from. These notes do not change calculations. "
                   "If you enter a hypothetical price, choose Your assumption rather than Public quote.")
        kinds = ["user_supplied_snapshot", "public_observation", "user_assumption", "synthetic_demo"]
        anchor_kind = st.selectbox("Starting price type", kinds, index=kinds.index(config["anchor"]["classification"]),
            format_func=lambda x: {"user_supplied_snapshot": "Supplied snapshot", "public_observation": "Public quote",
                                   "user_assumption": "Your assumption", "synthetic_demo": "Illustrative demo"}[x])
        anchor_date = st.text_input("Starting price date (YYYY-MM-DD)", config["anchor"]["as_of"],
            help="The chart starts in October 2026. Public quotes must be from that month.")
        anchor_url = st.text_input("Starting price source URL", config["anchor"]["source_url"],
            help="Required for a public quote. Use an HTTPS link to the source.")
        anchor_note = st.text_input("Starting price notes", config["anchor"]["note"])

    submitted = st.form_submit_button("Run scenario", type="primary")

if submitted:
    try:
        candidate = deepcopy(config)
        candidate["anchor"].update(price=price, classification=anchor_kind, as_of=anchor_date, source_url=anchor_url, note=anchor_note)
        candidate.update(n_paths=int(paths), seed=int(seed))
        candidate["settings"] = dict(settings, **eps)
        candidate["settings"].update(initial_regime=int(initial), initial_credit_stress=stress)
        candidate["selector"] = selector
        for original, row in zip(case_rows, case_edit.to_dict("records")):
            for y in range(2026, 2031):
                year = str(y)
                if row[year] != original[year]:
                    candidate["scenario_eps"][row["scenario"]][year] = config["scenario_eps"]["reference"][year] * (1 + float(row[year]) / 100)
        for i, weight in enumerate(weights["weight"]):
            if weight != config["priors"][i] * 100:
                candidate["priors"][i] = float(weight) / 100
        for i, adjustment in enumerate(premiums["adjustment_percent"]):
            if adjustment != premium_percentages[i]:
                candidate["regime_log_premiums"][i] = math.log1p(float(adjustment) / 100)
        candidate["events"] = [dict(row, classification="forecast_assumption") for row in event_edit.to_dict("records")]
        edited["manual_percentile"] = edited.manual_percentile.fillna(0.)
        candidate["monthly_overrides"] = [controls.iloc[0].to_dict(), *edited.to_dict("records")]
        with st.spinner("Running the simulation..."):
            result = run_model(candidate)
            overlay = compute_smart_selector(result)
        workspace["scenario"] = candidate
        workspace["run"] = (result, overlay)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"Scenario not applied: {input_error(exc)}")

if "run" not in workspace:
    try:
        result = run_model(config)
        workspace["run"] = (result, compute_smart_selector(result))
    except (ValueError, TypeError, KeyError) as exc:
        st.error(input_error(exc))
        st.stop()

result, overlay = workspace["run"]
st.session_state["run"] = (result, overlay)
c = result["config"]
view, view_overlay = for_display(result, overlay, display_currency, display_rate)
st.info(f"Showing {company['name']} · {c['n_paths']:,} simulated paths · starting price {SYMBOLS[native_currency]}{c['anchor']['price']:,.2f} {native_currency}. Click Run scenario to apply input edits.")
st.plotly_chart(chart_plotly(view, view_overlay), use_container_width=True)
st.caption("Blue: earnings reference. Green: median (P50). Amber: 80th percentile (P80). Magenta: your monthly selection. Gray: P10–P90 range. These are model scenarios, not guaranteed outcomes or measured market probabilities.")

output_tabs = st.tabs(["Monthly results", "Magenta line details", "Save & download"])
with output_tabs[0]:
    monthly_view = output_table(view, view_overlay)[["month", "earnings_reference", "p50", "p80", "p10", "p90", "selected_price", "percentile", "market_type"]]
    st.caption(f"Prices in {display_currency}. Full data and technical columns remain available in the CSV downloads.")
    st.dataframe(monthly_view.rename(columns={"month": "Month", "earnings_reference": "Blue reference", "p50": "Median (P50)",
        "p80": "80th percentile (P80)", "p10": "10th percentile (P10)", "p90": "90th percentile (P90)",
        "selected_price": "Magenta price", "percentile": "Magenta percentile", "market_type": "Market condition"}),
        hide_index=True, use_container_width=True)
with output_tabs[1]:
    details = view_overlay[["month", "selected_price", "percentile", "market_regime", "same_regime_count", "effective_sample_size", "clipped"]]
    st.dataframe(details.rename(columns={"month": "Month", "selected_price": "Magenta price", "percentile": "Percentile",
        "market_regime": "Market condition", "same_regime_count": "Paths in condition", "effective_sample_size": "Weighted matching paths",
        "clipped": "Limited by percentile bounds"}), hide_index=True, use_container_width=True)
    st.caption("Weighted matching paths shows how much independent support remains after weighting similar conditions. Full diagnostics are in the CSV.")
    st.caption("A rare manually requested regime can have too few matching paths. The tool reports this instead of substituting another regime. Increase Number of simulated paths in advanced settings, or change that month's selection.")
with output_tabs[2]:
    st.json(c, expanded=False)
    st.download_button("Download scenario JSON", json.dumps(c, indent=2), "scenario.json", "application/json")
    st.download_button("Download monthly regime CSV", pd.DataFrame(c["monthly_overrides"]).to_csv(index=False), "monthly_overrides.csv", "text/csv")
    st.download_button("Download monthly CSV", output_table(view, view_overlay).to_csv(index=False), "monthly.csv", "text/csv")
    diagnostics = view_overlay.copy()
    diagnostics["classification"] = "forecast_model_output"
    diagnostics.loc[0, "classification"] = c["anchor"]["classification"]
    diagnostics["notice"] = NOTICE
    diagnostics["company_id"] = selected_company
    diagnostics["currency"] = display_currency
    st.download_button("Download diagnostics CSV", diagnostics.to_csv(index=False), "selector.csv", "text/csv")
    st.download_button("Download standalone HTML report", html_report(view, view_overlay), "report.html", "text/html")
    st.download_button("Download inputs & source record (JSON)", json.dumps(audit_record(view, view_overlay), indent=2), "audit.json", "application/json")
with st.expander("Data sources and model notes"):
    st.write("AMD includes the original earnings forecasts, business events, starting case weights, historical return sample, and monthly selection settings. The published EPS figures below provide background; they do not replace your earnings assumptions." if selected_company == "AMD" else
             f"{company['name']} uses its own published EPS figure, dated public quote, and historical returns. Future earnings and event outcomes are demo assumptions, not company guidance or analyst consensus.")
    if c.get("sources"):
        st.json(c["sources"], expanded=False)
        st.json(c["forecast_notes"], expanded=False)
    st.json(result["meta"], expanded=False)
    st.dataframe(pd.DataFrame(public_facts(c)["facts"]), hide_index=True, use_container_width=True)
