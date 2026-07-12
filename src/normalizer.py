"""Normalize raw portfolio data into canonical schema for analysis."""

from .models import Portfolio, Holding
from typing import Any, Dict, List, Optional
import pandas as pd


def _normalize_holding(item: Dict[str, Any]) -> Holding:
    # `item` may come from a CSV/table where a blank cell is NaN (a float), not
    # an absent key or None — `or` catches both, unlike `dict.get(key, default)`.
    issuer = str(item.get("issuer") or item.get("name") or "").strip()
    market_value = float(item.get("market_value") or item.get("marketValue") or 0.0)
    weight_pct = float(item.get("weight_pct") or item.get("weight") or 0.0)
    return Holding(
        issuer=issuer,
        asset_type=str(item.get("asset_type") or item.get("asset_class") or "Unknown").strip() or "Unknown",
        sector=str(item.get("sector") or "Unknown").strip() or "Unknown",
        geography=str(item.get("geography") or item.get("country") or "Unknown").strip() or "Unknown",
        market_value=market_value,
        weight_pct=weight_pct,
        volatility_30d=item.get("volatility_30d") or item.get("volatility") or None,
        correlation_group=item.get("correlation_group") or None,
    )


def normalize_portfolio(raw: Dict[str, Any]) -> Portfolio:
    if not isinstance(raw, dict):
        raise ValueError("Portfolio payload must be a JSON object.")

    portfolio_id = str(raw.get("portfolio_id", raw.get("portfolioId", ""))).strip()
    fund = str(raw.get("fund", raw.get("fund_name", ""))).strip()
    if not portfolio_id:
        raise ValueError("portfolio_id is required")
    if not fund:
        raise ValueError("fund is required")

    holdings_raw: List[Dict[str, Any]] = raw.get("holdings", [])
    if not isinstance(holdings_raw, list) or not holdings_raw:
        raise ValueError("holdings must be a non-empty list")

    holdings = [_normalize_holding(item) for item in holdings_raw]
    total_market_value = sum(item.market_value for item in holdings)
    if total_market_value > 0:
        normalized_holdings = []
        for item in holdings:
            weight_pct = item.weight_pct
            if weight_pct <= 0:
                weight_pct = round(item.market_value / total_market_value * 100.0, 4)
            normalized_holdings.append(
                Holding(
                    issuer=item.issuer,
                    asset_type=item.asset_type,
                    sector=item.sector,
                    geography=item.geography,
                    market_value=item.market_value,
                    weight_pct=weight_pct,
                    volatility_30d=item.volatility_30d,
                    correlation_group=item.correlation_group,
                )
            )
        holdings = normalized_holdings

    return Portfolio(
        portfolio_id=portfolio_id,
        fund=fund,
        as_of=str(raw.get("as_of", raw.get("asOf", ""))).strip() or None,
        holdings=holdings,
    )


def dataframe_to_raw_portfolio(
    holdings_df: pd.DataFrame,
    portfolio_id: str,
    fund: str,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Turn a holdings table (CSV upload or manual entry grid) into a raw portfolio payload."""
    clean_df = holdings_df.dropna(how="all")
    # Cast to object first: pandas' native string dtype can't hold Python
    # None (it re-coerces blanks back to its own NA marker), only object can.
    clean_df = clean_df.astype(object).where(pd.notnull(clean_df), None)
    records = clean_df.to_dict("records")
    return {
        "portfolio_id": portfolio_id,
        "fund": fund,
        "as_of": as_of,
        "holdings": records,
    }
