from src.ai_client import generate_rationale


def test_generate_rationale_fallback_without_api_key():
    exposures = {
        "portfolio_id": "P1",
        "issuer_concentration": [],
        "sector_concentration": [],
        "geography_concentration": [],
        "correlation_flags": [],
    }
    rationale = generate_rationale(exposures, "LOW", 95.0)
    assert "Severity LOW" in rationale
    assert "rule-based analysis" in rationale
