from src.normalizer import normalize_portfolio


def test_normalize_portfolio_computes_weights():
    raw = {
        "portfolio_id": "PORT-123",
        "fund": "Test Fund",
        "holdings": [
            {"issuer": "Asset A", "asset_type": "Equity", "sector": "Tech", "geography": "US", "market_value": 100.0, "weight_pct": 0},
            {"issuer": "Asset B", "asset_type": "Bond", "sector": "Fixed Income", "geography": "US", "market_value": 100.0, "weight_pct": 0},
        ],
    }

    portfolio = normalize_portfolio(raw)
    assert portfolio.portfolio_id == "PORT-123"
    assert portfolio.fund == "Test Fund"
    assert len(portfolio.holdings) == 2
    assert round(portfolio.holdings[0].weight_pct, 4) == 50.0
    assert round(portfolio.holdings[1].weight_pct, 4) == 50.0
