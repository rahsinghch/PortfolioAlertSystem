from src.ai_client import generate_rationale


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_generate_rationale_fallback_without_api_key():
    exposures = {
        "portfolio_id": "P1",
        "issuer_concentration": [],
        "sector_concentration": [],
        "geography_concentration": [],
        "correlation_flags": [],
    }
    result = generate_rationale(exposures, "LOW", 95.0)
    assert "Severity LOW" in result["rationale"]
    assert "rule-based analysis" in result["rationale"]
    assert result["token_usage"] == {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def test_generate_rationale_parses_token_usage(monkeypatch):
    monkeypatch.setattr("src.ai_client.ANTHROPIC_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "message": {"content": [{"text": "Issuer concentration is the top risk driver."}]},
                "usage": {"input_tokens": 120, "output_tokens": 40},
            }
        )

    monkeypatch.setattr("src.ai_client.httpx.post", fake_post)

    exposures = {
        "issuer_concentration": [],
        "sector_concentration": [],
        "geography_concentration": [],
        "correlation_flags": [],
    }
    result = generate_rationale(exposures, "HIGH", 80.0)

    assert result["rationale"] == "Issuer concentration is the top risk driver."
    assert result["token_usage"] == {"input_tokens": 120, "output_tokens": 40, "total_tokens": 160}


def test_generate_rationale_zero_usage_on_request_failure(monkeypatch):
    monkeypatch.setattr("src.ai_client.ANTHROPIC_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        raise ConnectionError("network unreachable")

    monkeypatch.setattr("src.ai_client.httpx.post", fake_post)

    exposures = {
        "issuer_concentration": [],
        "sector_concentration": [],
        "geography_concentration": [],
        "correlation_flags": [],
    }
    result = generate_rationale(exposures, "MEDIUM", 70.0)

    assert "rule-based analysis" in result["rationale"]
    assert result["token_usage"] == {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
