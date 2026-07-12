"""Entry point for a Hugging Face Space or local Gradio demo."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import gradio as gr
except ImportError:
    gr = None

import pandas as pd

from .config import (
    ANTHROPIC_API_KEY,
    CORRELATION_THRESHOLD,
    DEFAULT_GEOGRAPHY_LIMIT,
    DEFAULT_ISSUER_LIMIT,
    DEFAULT_SECTOR_LIMIT,
)
from .data_loader import load_portfolio_json, load_portfolio_csv
from .normalizer import normalize_portfolio, dataframe_to_raw_portfolio
from .risk_engine import evaluate_exposures, score_severity
from .notifier import build_alert_actions, record_audit_entry, send_notifications
from .ai_client import generate_rationale
from .visualization import build_charts, STATUS_COLORS

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_PATH = DATA_DIR / "sample_portfolio.json"
CSV_TEMPLATE_PATH = DATA_DIR / "sample_holdings_template.csv"

CSV_SAMPLE_DOWNLOADS = {
    "CSV template (starter)": CSV_TEMPLATE_PATH,
    "CSV example: Diversified (Low risk)": DATA_DIR / "sample_holdings_diversified.csv",
    "CSV example: Concentrated (Critical risk)": DATA_DIR / "sample_holdings_concentrated.csv",
}

SAMPLE_PORTFOLIOS = {
    "Concentrated (Critical risk)": DATA_DIR / "sample_portfolio.json",
    "Geography concentration (High risk)": DATA_DIR / "sample_portfolio_geography_high_risk.json",
    "Emerging markets (Medium risk)": DATA_DIR / "sample_portfolio_moderate.json",
    "Correlation cluster flagged (Medium risk)": DATA_DIR / "sample_portfolio_correlation_flagged.json",
    "Diversified (Low risk)": DATA_DIR / "sample_portfolio_diversified.json",
}

SAMPLE_DESCRIPTIONS = {
    "Concentrated (Critical risk)": (
        "Two issuer breaches, one sector breach, and a correlated cluster — "
        "shows what a CRITICAL alert with multiple escalation actions looks like."
    ),
    "Geography concentration (High risk)": (
        "One geography (India) just over its 70% limit, with every issuer and sector "
        "otherwise clean — shows a single-breach HIGH alert, one notch below CRITICAL."
    ),
    "Emerging markets (Medium risk)": (
        "Issuer and sector weights sit near their limits (WARNING, not BREACH), plus a "
        "correlated cluster below the flag threshold — shows a MEDIUM alert with no breaches."
    ),
    "Correlation cluster flagged (Medium risk)": (
        "12 holdings sharing one correlation group add up to 85.8% combined weight — over "
        "the flag threshold (FLAGGED, not just WATCH) — while every individual issuer, sector, "
        "and geography stays within limits. Shows how a chart can flag red even when the "
        "overall severity is only MEDIUM."
    ),
    "Diversified (Low risk)": (
        "15 holdings spread across issuers, sectors, and geographies, all within limits — "
        "shows what a clean LOW severity result looks like."
    ),
}

HOLDING_COLUMNS = [
    "issuer",
    "asset_type",
    "sector",
    "geography",
    "market_value",
    "weight_pct",
    "volatility_30d",
    "correlation_group",
]

MANUAL_ENTRY_TEMPLATE = pd.DataFrame(
    [
        {
            "issuer": "Issuer A",
            "asset_type": "Equity",
            "sector": "Technology",
            "geography": "US",
            "market_value": 5000000,
            "weight_pct": 5.0,
            "volatility_30d": 0.15,
            "correlation_group": "",
        },
        {
            "issuer": "Issuer B",
            "asset_type": "Bond",
            "sector": "Financials",
            "geography": "Europe",
            "market_value": 5000000,
            "weight_pct": 5.0,
            "volatility_30d": 0.10,
            "correlation_group": "",
        },
    ],
    columns=HOLDING_COLUMNS,
)

EMPTY_CONCENTRATION = pd.DataFrame(columns=["key", "value_pct", "limit_pct", "status"])
EMPTY_CORRELATION = pd.DataFrame(columns=["group", "weight_pct", "count", "status"])
EMPTY_ALLOCATION = pd.DataFrame(columns=["asset_type", "weight_pct"])
EMPTY_HOLDINGS_TABLE = pd.DataFrame(columns=["issuer", "asset_type", "sector", "geography", "weight_pct", "market_value"])

SEVERITY_EMOJI = {"LOW": "\U0001F7E2", "MEDIUM": "\U0001F7E1", "HIGH": "\U0001F7E0", "CRITICAL": "\U0001F534"}


def analyze_portfolio(raw_portfolio: Dict[str, Any]) -> Dict[str, Any]:
    portfolio = normalize_portfolio(raw_portfolio)
    exposures = evaluate_exposures(portfolio)
    score = score_severity(exposures)
    rationale_result = generate_rationale(exposures, score["severity"], score["confidence"])
    action_objects = build_alert_actions(score["severity"])
    actions = [action.model_dump() for action in action_objects]
    audit_notes = record_audit_entry(portfolio.portfolio_id, f"Severity {score['severity']} with {len(actions)} escalation actions.")
    notification_results = send_notifications(portfolio.portfolio_id, score["severity"], action_objects)

    top_issuer = exposures["issuer_concentration"][0] if exposures["issuer_concentration"] else None
    portfolio_overview = {
        "holdings_count": len(portfolio.holdings),
        "total_market_value": round(sum(holding.market_value for holding in portfolio.holdings), 2),
        "top_position": (
            {"issuer": top_issuer["key"], "weight_pct": top_issuer["value_pct"]} if top_issuer else None
        ),
    }

    return {
        "portfolio_id": portfolio.portfolio_id,
        "fund": portfolio.fund,
        "as_of": portfolio.as_of,
        "severity": score["severity"],
        "confidence": score["confidence"],
        "rationale": rationale_result["rationale"],
        "token_usage": rationale_result["token_usage"],
        "portfolio_overview": portfolio_overview,
        "holdings": [holding.model_dump() for holding in portfolio.holdings],
        "exposures": exposures,
        "actions": actions,
        "audit_notes": audit_notes,
        "notification_results": notification_results,
        "anthropic_key_provided": bool(ANTHROPIC_API_KEY),
    }


def analyze_portfolio_json(json_text: str) -> Dict[str, Any]:
    raw_input = json.loads(json_text)
    return analyze_portfolio(raw_input)


def load_sample_portfolio() -> Dict[str, Any]:
    if not SAMPLE_PATH.exists():
        return {"error": "Sample portfolio file not found."}
    return load_portfolio_json(SAMPLE_PATH)


def _token_usage_markdown(token_usage: Dict[str, int]) -> str:
    total = token_usage.get("total_tokens", 0)
    if not total:
        return "**Tokens used:** 0 (rule-based fallback, no Claude call made)"
    return (
        f"**Tokens used:** {total} total "
        f"({token_usage.get('input_tokens', 0)} in / {token_usage.get('output_tokens', 0)} out)"
    )


def _portfolio_overview_markdown(overview: Dict[str, Any]) -> str:
    parts = [f"{overview['holdings_count']} holdings", f"${overview['total_market_value']:,.0f} total market value"]
    top_position = overview.get("top_position")
    if top_position:
        parts.append(f"largest position: {top_position['issuer']} ({top_position['weight_pct']}%)")
    return "**Portfolio snapshot:** " + " · ".join(parts)


def _severity_summary_markdown(result: Dict[str, Any]) -> str:
    emoji = SEVERITY_EMOJI.get(result["severity"], "⚪")
    return (
        f"### {emoji} Severity: {result['severity']}  |  Confidence: {result['confidence']}%\n\n"
        f"**Portfolio:** {result['portfolio_id']} ({result['fund']})\n\n"
        f"{result['rationale']}\n\n"
        f"{_portfolio_overview_markdown(result['portfolio_overview'])}\n\n"
        f"{_token_usage_markdown(result['token_usage'])}"
    )

def _error_markdown(message: str) -> str:
    return f"### ⚠️ Error\n{message}"


def _how_to_read_markdown() -> str:
    return (
        f"**Risk limits used:** issuer ≤ {DEFAULT_ISSUER_LIMIT}% · sector ≤ {DEFAULT_SECTOR_LIMIT}% · "
        f"geography ≤ {DEFAULT_GEOGRAPHY_LIMIT}% · correlation cluster flagged above "
        f"{CORRELATION_THRESHOLD * 100:.0f}% combined weight (configurable via `.env`).\n\n"
        "**Severity:**\n"
        "- 🟢 LOW — everything within limits, no action needed\n"
        "- 🟡 MEDIUM — a warning or a correlated cluster, worth keeping an eye on\n"
        "- 🟠 HIGH — one limit breached, review the position\n"
        "- 🔴 CRITICAL — multiple breaches, or one badly over its limit — act now\n\n"
        "**Chart colors** (same meaning in every chart): 🟢 OK · 🟡 WARNING (within 90% of the limit) · "
        "🔴 BREACH (over the limit) · 🟠 WATCH (correlated, under the flag threshold) · "
        "🔴 FLAGGED (correlated, over the flag threshold).\n\n"
        "**Portfolio Composition** (asset-type allocation) has no configured limit — it's a plain "
        "view of where the money sits, not a breach check. **Holdings Detail** lists every holding "
        "with its exact weight, as a plain-data alternative to the bar charts above."
    )


def _render(result: Dict[str, Any]) -> Tuple[Any, ...]:
    charts = build_charts(result["exposures"], result["severity"], result["confidence"], result["holdings"])
    return (
        result,
        _severity_summary_markdown(result),
        charts["issuer"],
        charts["sector"],
        charts["geography"],
        charts["correlation"],
        charts["asset_allocation"],
        charts["holdings_table"],
    )


def _error_render(message: str) -> Tuple[Any, ...]:
    return (
        {"error": message},
        _error_markdown(message),
        EMPTY_CONCENTRATION,
        EMPTY_CONCENTRATION,
        EMPTY_CONCENTRATION,
        EMPTY_CORRELATION,
        EMPTY_ALLOCATION,
        EMPTY_HOLDINGS_TABLE,
    )


def analyze_json_input(json_text: str) -> Tuple[Any, ...]:
    try:
        result = analyze_portfolio_json(json_text)
    except Exception as exc:
        return _error_render(str(exc))
    return _render(result)


def analyze_file_input(file_obj: Any, portfolio_id: str, fund: str, as_of: Optional[str]) -> Tuple[Any, ...]:
    if file_obj is None:
        return _error_render("Please upload a .json or .csv file.")

    path = Path(file_obj if isinstance(file_obj, str) else file_obj.name)
    try:
        if path.suffix.lower() == ".json":
            raw = load_portfolio_json(path)
        elif path.suffix.lower() == ".csv":
            holdings_df = load_portfolio_csv(path)
            raw = dataframe_to_raw_portfolio(
                holdings_df,
                portfolio_id or path.stem,
                fund or "Uploaded Fund",
                as_of or None,
            )
        else:
            raise ValueError("Unsupported file type. Upload a .json or .csv file.")
        result = analyze_portfolio(raw)
    except Exception as exc:
        return _error_render(str(exc))
    return _render(result)


def analyze_table_input(table_df: pd.DataFrame, portfolio_id: str, fund: str, as_of: Optional[str]) -> Tuple[Any, ...]:
    try:
        raw = dataframe_to_raw_portfolio(table_df, portfolio_id, fund, as_of or None)
        result = analyze_portfolio(raw)
    except Exception as exc:
        return _error_render(str(exc))
    return _render(result)


def analyze_sample_input(sample_label: str) -> Tuple[Any, ...]:
    try:
        path = SAMPLE_PORTFOLIOS[sample_label]
        raw = load_portfolio_json(path)
        result = analyze_portfolio(raw)
    except Exception as exc:
        return _error_render(str(exc))
    return _render(result)


def build_demo() -> Any:
    if gr is None:
        raise ImportError("Gradio is not installed. Install gradio to run the demo UI.")

    default_result = analyze_portfolio(load_sample_portfolio())
    default_charts = build_charts(
        default_result["exposures"],
        default_result["severity"],
        default_result["confidence"],
        default_result["holdings"],
    )

    with gr.Blocks(title="Portfolio Risk Alert System") as demo:
        gr.Markdown(
            "## Portfolio Risk Alert System\n"
            "Bring in portfolio data any of four ways below, then review severity, rationale, "
            "concentration risk charts, portfolio composition, and a full holdings table."
        )
        with gr.Accordion("How to read this analysis", open=False):
            gr.Markdown(_how_to_read_markdown())

        with gr.Tabs():
            with gr.TabItem("Paste JSON"):
                input_json = gr.Textbox(
                    lines=16,
                    label="Portfolio JSON",
                    value=json.dumps(load_sample_portfolio(), indent=2),
                )
                analyze_json_btn = gr.Button("Analyze Portfolio", variant="primary")

            with gr.TabItem("Upload File"):
                gr.Markdown(
                    "Upload a `.json` portfolio payload, or a `.csv` with one row per holding. "
                    "Not sure where to start? Download a template below, edit it, then upload it back.\n\n"
                    "**CSV columns:** `issuer` (name) · `asset_type` (Equity/Bond/...) · `sector` · "
                    "`geography` (country/region) · `market_value` (currency amount) · `weight_pct` "
                    "(% of portfolio; leave 0 to auto-compute from market_value) · `volatility_30d` "
                    "(optional, 0-1 scale) · `correlation_group` (optional; holdings sharing a group "
                    "are checked for correlated concentration). The Portfolio ID/Fund/As Of fields "
                    "below only apply to CSV uploads, since a holdings CSV has no place for that metadata."
                )
                with gr.Row():
                    for label, path in CSV_SAMPLE_DOWNLOADS.items():
                        gr.File(value=str(path), label=f"Download: {label}")
                    gr.File(value=str(SAMPLE_PATH), label="Download: JSON example")
                upload_file = gr.File(label="Portfolio file (.json or .csv)", file_types=[".json", ".csv"])
                with gr.Row():
                    upload_portfolio_id = gr.Textbox(label="Portfolio ID (CSV only)", value="UPLOAD-001")
                    upload_fund = gr.Textbox(label="Fund Name (CSV only)", value="Uploaded Fund")
                    upload_as_of = gr.Textbox(label="As Of (optional)")
                analyze_file_btn = gr.Button("Analyze Uploaded File", variant="primary")

            with gr.TabItem("Manual Entry"):
                gr.Markdown(
                    "Edit the holdings grid directly (add/remove rows), then analyze. "
                    "`weight_pct` is % of the portfolio (leave 0 to auto-compute from `market_value`); "
                    "`correlation_group` is optional — holdings sharing a group are checked together "
                    "for correlated concentration risk."
                )
                with gr.Row():
                    manual_portfolio_id = gr.Textbox(label="Portfolio ID", value="MANUAL-001")
                    manual_fund = gr.Textbox(label="Fund Name", value="Manual Entry Fund")
                    manual_as_of = gr.Textbox(label="As Of (optional)")
                manual_table = gr.Dataframe(
                    value=MANUAL_ENTRY_TEMPLATE,
                    headers=HOLDING_COLUMNS,
                    datatype=["str", "str", "str", "str", "number", "number", "number", "str"],
                    row_count=(2, "dynamic"),
                    column_count=(len(HOLDING_COLUMNS), "fixed"),
                    label="Holdings",
                )
                analyze_table_btn = gr.Button("Analyze Table", variant="primary")

            with gr.TabItem("Sample Portfolios"):
                gr.Markdown("Pick a pre-built sample to compare how different risk profiles look.")
                default_sample_label = list(SAMPLE_PORTFOLIOS.keys())[0]
                sample_dropdown = gr.Dropdown(
                    choices=list(SAMPLE_PORTFOLIOS.keys()),
                    value=default_sample_label,
                    label="Sample Portfolio",
                )
                sample_description = gr.Markdown(value=SAMPLE_DESCRIPTIONS[default_sample_label])
                analyze_sample_btn = gr.Button("Load & Analyze Sample", variant="primary")
                sample_dropdown.change(
                    fn=lambda label: SAMPLE_DESCRIPTIONS[label],
                    inputs=sample_dropdown,
                    outputs=sample_description,
                )

        gr.Markdown("---\n## Risk Analysis Result")
        severity_summary = gr.Markdown(value=_severity_summary_markdown(default_result))

        with gr.Row():
            issuer_chart = gr.BarPlot(
                value=default_charts["issuer"],
                x="key",
                y="value_pct",
                color="status",
                color_map=STATUS_COLORS,
                tooltip=["key", "value_pct", "limit_pct", "status"],
                x_title="Issuer",
                y_title="Weight %",
                title="Issuer Concentration vs Limit",
                label="Issuer Concentration",
            )
            sector_chart = gr.BarPlot(
                value=default_charts["sector"],
                x="key",
                y="value_pct",
                color="status",
                color_map=STATUS_COLORS,
                tooltip=["key", "value_pct", "limit_pct", "status"],
                x_title="Sector",
                y_title="Weight %",
                title="Sector Concentration vs Limit",
                label="Sector Concentration",
            )
        with gr.Row():
            geography_chart = gr.BarPlot(
                value=default_charts["geography"],
                x="key",
                y="value_pct",
                color="status",
                color_map=STATUS_COLORS,
                tooltip=["key", "value_pct", "limit_pct", "status"],
                x_title="Geography",
                y_title="Weight %",
                title="Geography Concentration vs Limit",
                label="Geography Concentration",
            )
            correlation_chart = gr.BarPlot(
                value=default_charts["correlation"],
                x="group",
                y="weight_pct",
                color="status",
                color_map=STATUS_COLORS,
                tooltip=["group", "weight_pct", "count", "status"],
                x_title="Correlation Cluster",
                y_title="Combined Weight %",
                title="Correlation Cluster Exposure",
                label="Correlation Clusters",
            )

        gr.Markdown("### Portfolio Composition")
        asset_allocation_chart = gr.BarPlot(
            value=default_charts["asset_allocation"],
            x="asset_type",
            y="weight_pct",
            tooltip=["asset_type", "weight_pct"],
            x_title="Asset Type",
            y_title="Weight %",
            title="Portfolio Composition by Asset Type",
            label="Asset Type Allocation",
        )

        gr.Markdown(
            "### Holdings Detail\n"
            "Every holding, sorted by weight — the exact numbers behind the charts above, "
            "and a plain-data alternative for anyone who can't read the bar charts."
        )
        holdings_table = gr.Dataframe(
            value=default_charts["holdings_table"],
            headers=["issuer", "asset_type", "sector", "geography", "weight_pct", "market_value"],
            label="Holdings",
            interactive=False,
        )

        output_json = gr.JSON(value=default_result, label="Full Analysis Output")

        outputs = [
            output_json,
            severity_summary,
            issuer_chart,
            sector_chart,
            geography_chart,
            correlation_chart,
            asset_allocation_chart,
            holdings_table,
        ]

        analyze_json_btn.click(fn=analyze_json_input, inputs=input_json, outputs=outputs)
        analyze_file_btn.click(
            fn=analyze_file_input,
            inputs=[upload_file, upload_portfolio_id, upload_fund, upload_as_of],
            outputs=outputs,
        )
        analyze_table_btn.click(
            fn=analyze_table_input,
            inputs=[manual_table, manual_portfolio_id, manual_fund, manual_as_of],
            outputs=outputs,
        )
        analyze_sample_btn.click(fn=analyze_sample_input, inputs=sample_dropdown, outputs=outputs)

    return demo


if __name__ == "__main__":
    if gr is None:
        print("Gradio is not installed. Install gradio with 'python -m pip install gradio' to run the demo.")
    else:
        app = build_demo()
        app.launch()
