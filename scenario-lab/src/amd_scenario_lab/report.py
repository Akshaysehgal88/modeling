"""Portable CSV, JSON and HTML exports. No network requests or CDN assets."""
from __future__ import annotations

from hashlib import sha256
from html import escape
from importlib.metadata import version
import json
from pathlib import Path
import platform

from .config import NOTICE, public_facts
from .catalog import company_info
from .currency import currency_context, SYMBOLS


def output_table(result, selector):
    columns = ["month", "smart_selected_price", "smart_percentile", "market_type",
               "selected_monthly_return_percent", "capped_to_p10_p90", "selector_source",
               "selected_price", "percentile"]
    table = result["monthly"].merge(selector[columns], on="month", validate="one_to_one")
    table["classification"] = "forecast_model_output"
    table.loc[0, "classification"] = result["config"]["anchor"]["classification"]
    table["anchor_classification"] = result["config"]["anchor"]["classification"]
    table["notice"] = NOTICE
    info = company_info(result["config"])
    display = currency_context(result)
    table["company_id"] = info["id"]
    table["symbol"] = info["symbol"]
    table["currency"] = display["currency"]
    table["native_currency"] = info["currency"]
    table["display_fx_rate"] = display["rate"]
    return table


def audit_record(result, selector):
    config_json = json.dumps(result["config"], sort_keys=True, allow_nan=False)
    return {"schema_version": 2, "package_version": "2.0.0",
            "runtime": {"python": platform.python_version(),
                        "numpy": version("numpy"), "pandas": version("pandas")},
            "config_sha256": sha256(config_json.encode()).hexdigest(),
            "meta": result["meta"], "config": result["config"],
            "public_facts": public_facts(result["config"]),
            "instrument": company_info(result["config"]), "display": currency_context(result),
            "month_end_touch_frequencies": result["touches"],
            "month_end_touch_frequency_currency": company_info(result["config"])["currency"],
            "selector_path_index": int(selector.path_index.iloc[0]),
            "input_provenance": {
                "forecast_settings": ("Original scenario assumptions, preserved" if company_info(result["config"])["id"] == "AMD" else "Company-specific authored forecast assumptions; public EPS base recorded separately"),
                "event_notes": "Scenario narratives and timing assumptions, not independently verified announcements",
                "calibration": result["meta"]["calibration_source"]},
            "methodology": "See docs/METHODOLOGY.md for the preserved original equations and regression results."}


def chart_plotly(result, selector):
    from ._core import chart_plotly as original_chart
    figure = original_chart(result, selector=selector)
    info = company_info(result["config"])
    display = currency_context(result)
    if info["id"] != "AMD" or display["currency"] != "USD":
        symbol = SYMBOLS[display["currency"]]
        figure.update_layout(title=f"{info['name']} | Market-regime model + adaptive percentile selector (October 2026)",
                             yaxis_title=f"{display['currency']} per {info['unit'].replace('_', ' ')}",
                             yaxis_tickprefix=symbol)
        for trace in figure.data:
            if trace.hovertemplate:
                trace.hovertemplate = trace.hovertemplate.replace("$", symbol)
    return figure


def html_report(result, selector):
    """Build a data-only standalone report without an HTML/JS dependency."""
    d = result["monthly"]
    info = company_info(result["config"])
    display = currency_context(result)
    symbol = SYMBOLS[display["currency"]]
    series = [("Reference", d.earnings_reference.to_numpy(), "#5688e5"),
              ("P50", d.p50.to_numpy(), "#18a58a"), ("P80", d.p80.to_numpy(), "#d69327"),
              ("Adaptive scenario", selector.selected_price.to_numpy(), "#b95ca2")]
    maximum = float(d.p90.max()) * 1.08
    def points(values):
        return " ".join(f"{60 + i * 880 / (len(d)-1):.2f},{350 - float(y) * 310 / maximum:.2f}" for i, y in enumerate(values))
    band = points(d.p90) + " " + " ".join(reversed(points(d.p10).split()))
    chart = f'<svg viewBox="0 0 1000 410" role="img" aria-label="Illustrative forecast with model percentiles"><polygon points="{band}" fill="#e2eaf3"/>'
    for name, values, color in series:
        chart += f'<polyline points="{points(values)}" fill="none" stroke="{color}" stroke-width="3"><title>{escape(name)}</title></polyline>'
    for i in range(5):
        v = maximum * i / 4
        chart += f'<text x="2" y="{355-i*310/4:.1f}" font-size="12">{escape(symbol)}{v:.0f}</text>'
    chart += f'<text x="60" y="385">{escape(d.month.iloc[0])}</text><text x="870" y="385">{escape(d.month.iloc[-1])}</text></svg>'
    legend = " | ".join(f'<span style="color:{color}">{escape(name)}</span>' for name, _, color in series)
    sources = "".join(f'<li>{escape(f["period"])} {escape(f["basis"])} EPS {escape(f.get("currency", "USD"))} {f["value"]:.2f} - <a href="{escape(f["source_url"], quote=True)}">Issuer disclosure</a></li>' for f in public_facts(result["config"])["facts"])
    config = result["config"]
    basis = result["earnings_basis"]
    audit = escape(json.dumps(audit_record(result, selector), indent=2, allow_nan=False))
    diagnostics = selector.copy()
    diagnostics["classification"] = "forecast_model_output"
    diagnostics.loc[0, "classification"] = config["anchor"]["classification"]
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scenario Lab - {escape(info["name"])} forecast</title><style>
body{{font:16px/1.55 system-ui,sans-serif;background:#f5f7fa;color:#183046;margin:0}}
main{{max-width:1100px;margin:auto;padding:32px}}h1{{letter-spacing:-.03em}}.notice{{padding:16px;border-left:4px solid #c48218;background:#fff4db}}
.panel{{background:white;border:1px solid #dde4eb;border-radius:12px;padding:20px;margin:20px 0;overflow:auto}}svg{{width:100%;min-width:480px}}
table{{border-collapse:collapse;font-size:13px}}td,th{{border-bottom:1px solid #dde4eb;padding:8px;text-align:right;white-space:nowrap}}pre{{white-space:pre-wrap;font-size:13px}}a{{color:#245fb5}}
</style><main><h1>Scenario Lab · {escape(info["name"])}</h1><p>{escape(config['title'])}</p>
<p class="notice">{escape(NOTICE)}<br><strong>Anchor: {escape(config['anchor']['classification'])}, {escape(symbol)}{config['anchor']['price'] * display['rate']:.2f} {display['currency']}, {escape(config['anchor']['as_of'])}.</strong><br>{escape(config['anchor']['note'])}</p>
<p>Instrument: {escape(info['symbol'])} · {escape(info['exchange'])} · native {escape(info['currency'])}. Display FX: {display['rate']:.8g} {display['currency']} per {info['currency']}. Earnings basis: {escape(basis)}. All forward earnings, event outcomes, model weights and valuation multiples are forecast assumptions. P10-P90 is a model range, not a confidence interval.</p>
<section class="panel">{chart}<p>{legend}</p><p>Gray: P10-P90. The adaptive overlay uses hypothetical future conditions. Conditional monthly medians and percentile curves need not form one simulated trading path.</p></section>
<section class="panel"><h2>Monthly model outputs</h2>{output_table(result, selector).round(4).to_html(index=False, escape=True)}</section>
<section class="panel"><h2>Selector diagnostics</h2>{diagnostics.round(4).to_html(index=False, escape=True)}</section>
<section class="panel"><h2>Input provenance</h2><p>{escape(result['meta']['calibration_source'])}. Earnings curves, event outcomes and market parameters are scenario assumptions. Issuer EPS references, quote/history sources and any display FX are recorded separately in the audit. This preset retains its own instrument inputs and assumptions.</p><ul>{sources}</ul></section>
<details class="panel"><summary>Configuration and provenance</summary><pre>{audit}</pre></details></main></html>'''


def export_result(result, selector, directory):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    output_table(result, selector).to_csv(out / "monthly.csv", index=False)
    diagnostics = selector.copy()
    diagnostics["classification"] = "forecast_model_output"
    diagnostics.loc[0, "classification"] = result["config"]["anchor"]["classification"]
    diagnostics["notice"] = NOTICE
    info = company_info(result["config"])
    display = currency_context(result)
    diagnostics["company_id"] = info["id"]
    diagnostics["symbol"] = info["symbol"]
    diagnostics["currency"] = display["currency"]
    diagnostics["native_currency"] = info["currency"]
    diagnostics["display_fx_rate"] = display["rate"]
    diagnostics.to_csv(out / "selector.csv", index=False)
    (out / "audit.json").write_text(json.dumps(audit_record(result, selector), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "report.html").write_text(html_report(result, selector), encoding="utf-8")
    import pandas as pd
    pd.DataFrame(result["config"]["monthly_overrides"]).to_csv(out / "monthly_overrides.csv", index=False)
    return out
