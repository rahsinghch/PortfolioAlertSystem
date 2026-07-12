from src.visualization import build_charts, concentration_dataframe, correlation_dataframe


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


def test_build_charts_bundles_all_categories():
    exposures = {
        "issuer_concentration": [{"key": "A", "value_pct": 10.0, "limit_pct": 8.0, "status": "BREACH"}],
        "sector_concentration": [{"key": "Energy", "value_pct": 20.0, "limit_pct": 25.0, "status": "OK"}],
        "geography_concentration": [{"key": "US", "value_pct": 30.0, "limit_pct": 70.0, "status": "OK"}],
        "correlation_flags": [],
    }
    charts = build_charts(exposures, "HIGH", 80.0)
    assert set(charts.keys()) == {"issuer", "sector", "geography", "correlation", "severity"}
    assert len(charts["issuer"]) == 1
    assert charts["correlation"].empty
    assert charts["severity"].iloc[0]["severity"] == "HIGH"
