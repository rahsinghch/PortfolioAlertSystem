from src.visualization import (
    asset_type_allocation_dataframe,
    build_charts,
    concentration_dataframe,
    correlation_dataframe,
    holdings_table_dataframe,
)


def test_concentration_dataframe_columns():
    records = [{"category": "issuer", "key": "Issuer A", "value_pct": 12.0, "limit_pct": 8.0, "status": "BREACH"}]
    df = concentration_dataframe(records)
    assert list(df.columns) == ["key", "value_pct", "limit_pct", "status"]
    assert df.iloc[0]["status"] == "BREACH"


def test_concentration_dataframe_empty():
    df = concentration_dataframe([])
    assert df.empty
    assert list(df.columns) == ["key", "value_pct", "limit_pct", "status"]


def test_correlation_dataframe_columns():
    records = [{"group": "cluster-1", "weight_pct": 32.2, "count": 2, "status": "WATCH", "assets": ["A", "B"]}]
    df = correlation_dataframe(records)
    assert list(df.columns) == ["group", "weight_pct", "count", "status"]
    assert df.iloc[0]["count"] == 2


def test_asset_type_allocation_dataframe_aggregates_by_type():
    holdings = [
        {"asset_type": "Equity", "weight_pct": 30.0},
        {"asset_type": "Equity", "weight_pct": 20.0},
        {"asset_type": "Bond", "weight_pct": 50.0},
    ]
    df = asset_type_allocation_dataframe(holdings)
    assert list(df.columns) == ["asset_type", "weight_pct"]
    by_type = dict(zip(df["asset_type"], df["weight_pct"]))
    assert by_type["Equity"] == 50.0
    assert by_type["Bond"] == 50.0


def test_asset_type_allocation_dataframe_empty():
    df = asset_type_allocation_dataframe([])
    assert df.empty
    assert list(df.columns) == ["asset_type", "weight_pct"]


def test_holdings_table_dataframe_sorted_by_weight_descending():
    holdings = [
        {"issuer": "Small", "asset_type": "Bond", "sector": "Tech", "geography": "US", "weight_pct": 5.0, "market_value": 5},
        {"issuer": "Big", "asset_type": "Equity", "sector": "Energy", "geography": "India", "weight_pct": 40.0, "market_value": 40},
    ]
    df = holdings_table_dataframe(holdings)
    assert list(df.columns) == ["issuer", "asset_type", "sector", "geography", "weight_pct", "market_value"]
    assert df.iloc[0]["issuer"] == "Big"
    assert df.iloc[1]["issuer"] == "Small"


def test_holdings_table_dataframe_empty():
    df = holdings_table_dataframe([])
    assert df.empty
    assert list(df.columns) == ["issuer", "asset_type", "sector", "geography", "weight_pct", "market_value"]


def test_build_charts_bundles_all_categories():
    exposures = {
        "issuer_concentration": [{"key": "A", "value_pct": 10.0, "limit_pct": 8.0, "status": "BREACH"}],
        "sector_concentration": [{"key": "Energy", "value_pct": 20.0, "limit_pct": 25.0, "status": "OK"}],
        "geography_concentration": [{"key": "US", "value_pct": 30.0, "limit_pct": 70.0, "status": "OK"}],
        "correlation_flags": [],
    }
    holdings = [{"issuer": "A", "asset_type": "Equity", "sector": "Energy", "geography": "US", "weight_pct": 10.0, "market_value": 100.0}]
    charts = build_charts(exposures, "HIGH", 80.0, holdings)
    assert set(charts.keys()) == {"issuer", "sector", "geography", "correlation", "severity", "asset_allocation", "holdings_table"}
    assert len(charts["issuer"]) == 1
    assert charts["correlation"].empty
    assert charts["severity"].iloc[0]["severity"] == "HIGH"
    assert len(charts["asset_allocation"]) == 1
    assert len(charts["holdings_table"]) == 1


def test_build_charts_defaults_holdings_to_empty():
    exposures = {"issuer_concentration": [], "sector_concentration": [], "geography_concentration": [], "correlation_flags": []}
    charts = build_charts(exposures, "LOW", 50.0)
    assert charts["asset_allocation"].empty
    assert charts["holdings_table"].empty
