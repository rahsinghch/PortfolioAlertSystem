import io

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


def test_dataframe_to_raw_portfolio_handles_blank_optional_cells():
    # A column with some blank cells and some filled ones (like correlation_group
    # in a real CSV) parses as pandas' native string dtype, where a blank cell
    # is its own NA marker rather than Python None or NaN as `object` dtype
    # would give — this must still normalize cleanly instead of failing
    # Pydantic validation on the blank rows.
    csv_text = (
        "issuer,asset_type,sector,geography,market_value,weight_pct,correlation_group\n"
        "Asset A,Equity,Tech,US,100,50,\n"
        "Asset B,Bond,Fixed Income,US,100,50,cluster-1\n"
    )
    df = pd.read_csv(io.StringIO(csv_text))

    raw = dataframe_to_raw_portfolio(df, "CSV-003", "CSV Fund")
    portfolio = normalize_portfolio(raw)

    assert portfolio.holdings[0].correlation_group is None
    assert portfolio.holdings[1].correlation_group == "cluster-1"
