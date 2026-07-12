import pandas as pd

from src.normalizer import dataframe_to_raw_portfolio, normalize_portfolio


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


def test_dataframe_to_raw_portfolio_builds_expected_shape():
    df = pd.DataFrame(
        [
            {"issuer": "Asset A", "asset_type": "Equity", "sector": "Tech", "geography": "US", "market_value": 100.0, "weight_pct": 10.0},
            {"issuer": "Asset B", "asset_type": "Bond", "sector": "Fixed Income", "geography": "US", "market_value": 200.0, "weight_pct": 20.0},
        ]
    )

    raw = dataframe_to_raw_portfolio(df, "CSV-001", "CSV Fund", "2026-07-12")

    assert raw["portfolio_id"] == "CSV-001"
    assert raw["fund"] == "CSV Fund"
    assert raw["as_of"] == "2026-07-12"
    assert len(raw["holdings"]) == 2

    portfolio = normalize_portfolio(raw)
    assert portfolio.holdings[0].issuer == "Asset A"


def test_dataframe_to_raw_portfolio_drops_blank_rows():
    df = pd.DataFrame(
        [
            {"issuer": "Asset A", "asset_type": "Equity", "sector": "Tech", "geography": "US", "market_value": 100.0, "weight_pct": 10.0},
            {"issuer": None, "asset_type": None, "sector": None, "geography": None, "market_value": None, "weight_pct": None},
        ]
    )

    raw = dataframe_to_raw_portfolio(df, "CSV-002", "CSV Fund")

    assert len(raw["holdings"]) == 1
