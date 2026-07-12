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


def build_charts(exposures: Dict[str, Any], severity: str, confidence: float) -> Dict[str, pd.DataFrame]:
    """Bundle every chart DataFrame needed to render the risk visualization panel."""
    return {
        "issuer": concentration_dataframe(exposures.get("issuer_concentration", [])),
        "sector": concentration_dataframe(exposures.get("sector_concentration", [])),
        "geography": concentration_dataframe(exposures.get("geography_concentration", [])),
        "correlation": correlation_dataframe(exposures.get("correlation_flags", [])),
        "severity": severity_dataframe(severity, confidence),
    }
