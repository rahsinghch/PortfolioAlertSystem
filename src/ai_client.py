"""Anthropic Claude client wrapper and prompt helper."""

from typing import Dict, Any
import httpx
from .config import ANTHROPIC_API_KEY, ANTHROPIC_API_URL, ANTHROPIC_MODEL

SYSTEM_PROMPT = (
    "You are an AI risk analyst. Analyze portfolio exposure findings and generate a concise, human-readable rationale for the alert. "
    "Return only a single paragraph describing the top risk drivers, severity context, and recommended next steps."
)

ZERO_TOKEN_USAGE: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _build_prompt(exposures: Dict[str, Any], severity: str, confidence: float) -> str:
    exposure_lines = []
    for category in ["issuer_concentration", "sector_concentration", "geography_concentration"]:
        for record in exposures.get(category, []):
            if record["status"] in ["BREACH", "WARNING"]:
                exposure_lines.append(
                    f"{record['category'].capitalize()} {record['key']} is {record['status']} at {record['value_pct']}% (limit {record['limit_pct']}%)."
                )

    correlation_lines = []
    for record in exposures.get("correlation_flags", []):
        correlation_lines.append(
            f"Correlation cluster {record['group']} includes {record['count']} assets at {record['weight_pct']}% weight and is {record['status']}."
        )

    if not exposure_lines and not correlation_lines:
        exposure_lines.append("All concentration and geography limits are within tolerance.")

    prompt = [
        f"Severity: {severity}",
        f"Confidence: {confidence}%",
        "Exposure findings:",
        *exposure_lines,
    ]
    if correlation_lines:
        prompt.extend(["Correlation findings:", *correlation_lines])
    prompt.append("Provide a short alert rationale.")
    return "\n".join(prompt)


def _parse_response(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    if "completion" in payload:
        completion = payload["completion"]
        if isinstance(completion, dict):
            return str(completion.get("text", "")).strip()
        return str(completion).strip()
    if "message" in payload:
        message = payload["message"]
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    return str(first.get("text", "")).strip()
        return str(message).strip()
    return str(payload.get("output", "")).strip()


def _parse_token_usage(payload: Dict[str, Any]) -> Dict[str, int]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return dict(ZERO_TOKEN_USAGE)
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def generate_rationale(exposures: Dict[str, Any], severity: str, confidence: float) -> Dict[str, Any]:
    fallback_rationale = f"Severity {severity} with confidence {confidence}%. Exposures evaluated by rule-based analysis."

    if not ANTHROPIC_API_KEY:
        return {"rationale": fallback_rationale, "token_usage": dict(ZERO_TOKEN_USAGE)}

    request_payload = {
        "model": ANTHROPIC_MODEL,
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "text", "text": _build_prompt(exposures, severity, confidence)}]}
        ]
    }

    try:
        response = httpx.post(
            f"{ANTHROPIC_API_URL}/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
            },
            json=request_payload,
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "rationale": _parse_response(payload) or fallback_rationale,
            "token_usage": _parse_token_usage(payload),
        }
    except Exception:
        return {"rationale": fallback_rationale, "token_usage": dict(ZERO_TOKEN_USAGE)}
