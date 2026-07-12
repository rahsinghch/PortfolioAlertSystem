"""Entry point for a Hugging Face Space or local Gradio demo."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import gradio as gr
except ImportError:
    gr = None

import pandas as pd

from .config import ANTHROPIC_API_KEY
from .data_loader import load_portfolio_json, load_portfolio_csv
from .normalizer import normalize_portfolio, dataframe_to_raw_portfolio
from .risk_engine import evaluate_exposures, score_severity
from .notifier import build_alert_actions, record_audit_entry, send_notifications
from .ai_client import generate_rationale
from .visualization import build_charts, STATUS_COLORS

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_PATH = DATA_DIR / "sample_portfolio.json"

SAMPLE_PORTFOLIOS = {
    "Concentrated (Critical risk)": DATA_DIR / "sample_portfolio.json",
    "Emerging markets (Medium risk)": DATA_DIR / "sample_portfolio_moderate.json",
    "Diversified (Low risk)": DATA_DIR / "sample_portfolio_diversified.json",
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

SEVERITY_EMOJI = {"LOW": "\U0001F7E2", "MEDIUM": "\U0001F7E1", "HIGH": "\U0001F7E0", "CRITICAL": "\U0001F534"}


def analyze_portfolio(raw_portfolio: Dict[str, Any]) -> Dict[str, Any]:
    portfolio = normalize_portfolio(raw_portfolio)
    exposures = evaluate_exposures(portfolio)
    score = score_severity(exposures)
    rationale = generate_rationale(exposures, score["severity"], score["confidence"])
    action_objects = build_alert_actions(score["severity"])
    actions = [action.model_dump() for action in action_objects]
    audit_notes = record_audit_entry(portfolio.portfolio_id, f"Severity {score['severity']} with {len(actions)} escalation actions.")
    notification_results = send_notifications(portfolio.portfolio_id, score["severity"], action_objects)

    return {
        "portfolio_id": portfolio.portfolio_id,
        "fund": portfolio.fund,
        "as_of": portfolio.as_of,
        "severity": score["severity"],
        "confidence": score["confidence"],
        "rationale": rationale,
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


def _severity_summary_markdown(result: Dict[str, Any]) -> str:
    emoji = SEVERITY_EMOJI.get(result["severity"], "⚪")
    return (
        f"### {emoji} Severity: {result['severity']}  |  Confidence: {result['confidence']}%\n\n"
        f"**Portfolio:** {result['portfolio_id']} ({result['fund']})\n\n"
        f"{result['rationale']}"
    )

def _error_markdown(message: str) -> str:
    return f"### ⚠️ Error\n{message}"


def _render(result: Dict[str, Any]) -> Tuple[Any, ...]:
    charts = build_charts(result["exposures"], result["severity"], result["confidence"])
    return (
        result,
        _severity_summary_markdown(result),
        charts["issuer"],
        charts["sector"],
        charts["geography"],
        charts["correlation"],
    )


def _error_render(message: str) -> Tuple[Any, ...]:
    return (
        {"error": message},
        _error_markdown(message),
        EMPTY_CONCENTRATION,
        EMPTY_CONCENTRATION,
        EMPTY_CONCENTRATION,
        EMPTY_CORRELATION,
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
    default_charts = build_charts(default_result["exposures"], default_result["severity"], default_result["confidence"])

    with gr.Blocks(title="Portfolio Risk Alert System") as demo:
        gr.Markdown(
            "## Portfolio Risk Alert System\n"
            "Bring in portfolio data any of four ways below, then review severity, rationale, "
            "and concentration risk charts."
        )

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
                    "Upload a `.json` portfolio payload, or a `.csv` with one row per holding "
                    "(columns: `issuer, asset_type, sector, geography, market_value, weight_pct, "
                    "volatility_30d, correlation_group`). The fields below only apply to CSV uploads."
                )
                upload_file = gr.File(label="Portfolio file (.json or .csv)", file_types=[".json", ".csv"])
                with gr.Row():
                    upload_portfolio_id = gr.Textbox(label="Portfolio ID (CSV only)", value="UPLOAD-001")
                    upload_fund = gr.Textbox(label="Fund Name (CSV only)", value="Uploaded Fund")
                    upload_as_of = gr.Textbox(label="As Of (optional)")
                analyze_file_btn = gr.Button("Analyze Uploaded File", variant="primary")

            with gr.TabItem("Manual Entry"):
                gr.Markdown("Edit the holdings grid directly (add/remove rows), then analyze.")
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
                sample_dropdown = gr.Dropdown(
                    choices=list(SAMPLE_PORTFOLIOS.keys()),
                    value=list(SAMPLE_PORTFOLIOS.keys())[0],
                    label="Sample Portfolio",
                )
                analyze_sample_btn = gr.Button("Load & Analyze Sample", variant="primary")

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

        output_json = gr.JSON(value=default_result, label="Full Analysis Output")

        outputs = [output_json, severity_summary, issuer_chart, sector_chart, geography_chart, correlation_chart]

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
