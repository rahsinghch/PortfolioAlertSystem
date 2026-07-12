"""Entry point for a Hugging Face Space or local Gradio demo."""

import json
from pathlib import Path
from typing import Any, Dict

try:
    import gradio as gr
except ImportError:
    gr = None

from .config import ANTHROPIC_API_KEY
from .data_loader import load_portfolio_json
from .normalizer import normalize_portfolio
from .risk_engine import evaluate_exposures, score_severity
from .notifier import build_alert_actions, record_audit_entry, send_notifications
from .ai_client import generate_rationale

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_portfolio.json"


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


def build_demo() -> Any:
    if gr is None:
        raise ImportError("Gradio is not installed. Install gradio to run the demo UI.")

    with gr.Blocks(title="Portfolio Risk Alert System") as demo:
        gr.Markdown("## Portfolio Risk Alert System\nUpload a portfolio JSON or paste payload to see risk exposure analysis and alert generation.")

        input_json = gr.Textbox(lines=18, label="Portfolio JSON", value=json.dumps(load_sample_portfolio(), indent=2))
        output = gr.JSON(label="Analysis Output")

        analyze_button = gr.Button("Analyze Portfolio")
        analyze_button.click(fn=analyze_portfolio_json, inputs=input_json, outputs=output)

    return demo


if __name__ == "__main__":
    if gr is None:
        print("Gradio is not installed. Install gradio with 'python -m pip install gradio' to run the demo.")
    else:
        app = build_demo()
        app.launch()
