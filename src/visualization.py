"""Build chart-ready pandas DataFrames for portfolio risk visualizations.

Colors follow a fixed status palette (never themed, never reused for
series identity) so severity always reads the same way across charts:
good / warning / serious / critical.
"""

from typing import Any, Dict, List
import pandas as pd

STATUS_COLORS: Dict[str, str] = {
    "OK": "#0ca30c",
    "WARNING": "#fab219",
    "BREACH": "#d03b3b",
    "WATCH": "#ec835a",
    "FLAGGED": "#d03b3b",
}

SEVERITY_COLORS: Dict[str, str] = {
    "LOW": "#0ca30c",
    "MEDIUM": "#fab219",
    "HIGH": "#ec835a",
    "CRITICAL": "#d03b3b",
}


def concentration_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """One row per issuer/sector/geography with its weight, limit, and status."""
    if not records:
        return pd.DataFrame(columns=["key", "value_pct", "limit_pct", "status"])
    return pd.DataFrame(
        [
            {
                "key": record["key"],
                "value_pct": record["value_pct"],
                "limit_pct": record["limit_pct"],
                "status": record["status"],
            }
            for record in records
        ]
    )


def correlation_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """One row per correlated asset cluster with its combined weight and status."""
    if not records:
        return pd.DataFrame(columns=["group", "weight_pct", "count", "status"])
    return pd.DataFrame(
        [
            {
                "group": record["group"],
                "weight_pct": record["weight_pct"],
                "count": record["count"],
                "status": record["status"],
            }
            for record in records
        ]
    )


def severity_dataframe(severity: str, confidence: float) -> pd.DataFrame:
    """Single-bar summary of the overall alert severity and model confidence."""
    return pd.DataFrame([{"metric": "Confidence %", "value": confidence, "severity": severity}])


def asset_type_allocation_dataframe(holdings: List[Dict[str, Any]]) -> pd.DataFrame:
    """Portfolio composition by asset type (Equity/Bond/...), not a risk-limit check.

    No configured limit applies to asset type today, so this is a plain
    magnitude view of "where the money sits" rather than a status-colored
    breach chart.
    """
    if not holdings:
        return pd.DataFrame(columns=["asset_type", "weight_pct"])
    totals: Dict[str, float] = {}
    for holding in holdings:
        asset_type = holding.get("asset_type", "Unknown")
        totals[asset_type] = totals.get(asset_type, 0.0) + holding.get("weight_pct", 0.0)
    rows = [{"asset_type": key, "weight_pct": round(value, 4)} for key, value in totals.items()]
    rows.sort(key=lambda row: row["weight_pct"], reverse=True)
    return pd.DataFrame(rows)


def holdings_table_dataframe(holdings: List[Dict[str, Any]]) -> pd.DataFrame:
    """One row per holding, sorted by weight descending — a plain-data view
    that complements the aggregated charts and gives screen-reader/print
    users a table alternative to the bar charts.
    """
    columns = ["issuer", "asset_type", "sector", "geography", "weight_pct", "market_value"]
    if not holdings:
        return pd.DataFrame(columns=columns)
    rows = [
        {
            "issuer": holding.get("issuer", ""),
            "asset_type": holding.get("asset_type", ""),
            "sector": holding.get("sector", ""),
            "geography": holding.get("geography", ""),
            "weight_pct": round(holding.get("weight_pct", 0.0), 4),
            "market_value": holding.get("market_value", 0.0),
        }
        for holding in holdings
    ]
    rows.sort(key=lambda row: row["weight_pct"], reverse=True)
    return pd.DataFrame(rows, columns=columns)


def build_charts(
    exposures: Dict[str, Any],
    severity: str,
    confidence: float,
    holdings: List[Dict[str, Any]] = None,
) -> Dict[str, pd.DataFrame]:
    """Bundle every chart/table DataFrame needed to render the risk visualization panel."""
    holdings = holdings or []
    return {
        "issuer": concentration_dataframe(exposures.get("issuer_concentration", [])),
        "sector": concentration_dataframe(exposures.get("sector_concentration", [])),
        "geography": concentration_dataframe(exposures.get("geography_concentration", [])),
        "correlation": correlation_dataframe(exposures.get("correlation_flags", [])),
        "severity": severity_dataframe(severity, confidence),
        "asset_allocation": asset_type_allocation_dataframe(holdings),
        "holdings_table": holdings_table_dataframe(holdings),
    }
