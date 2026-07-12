"""Compute concentration exposures and severity scoring for portfolios."""

from typing import Dict, Any, List
from .models import Portfolio
from .config import DEFAULT_ISSUER_LIMIT, DEFAULT_SECTOR_LIMIT, DEFAULT_GEOGRAPHY_LIMIT, CORRELATION_THRESHOLD


def _classify_status(value: float, limit: float) -> str:
    if value > limit:
        return "BREACH"
    if value >= limit * 0.9:
        return "WARNING"
    return "OK"


def _build_exposure_record(category: str, key: str, value: float, limit: float) -> Dict[str, Any]:
    return {
        "category": category,
        "key": key,
        "value_pct": round(value, 4),
        "limit_pct": limit,
        "status": _classify_status(value, limit),
    }


def evaluate_exposures(portfolio: Portfolio) -> Dict[str, Any]:
    issuer_totals: Dict[str, float] = {}
    sector_totals: Dict[str, float] = {}
    geography_totals: Dict[str, float] = {}
    correlation_groups: Dict[str, Dict[str, Any]] = {}

    for holding in portfolio.holdings:
        issuer_totals[holding.issuer] = issuer_totals.get(holding.issuer, 0.0) + holding.weight_pct
        sector_totals[holding.sector] = sector_totals.get(holding.sector, 0.0) + holding.weight_pct
        geography_totals[holding.geography] = geography_totals.get(holding.geography, 0.0) + holding.weight_pct

        if holding.correlation_group:
            group = correlation_groups.setdefault(holding.correlation_group, {"count": 0, "weight_pct": 0.0, "assets": []})
            group["count"] += 1
            group["weight_pct"] += holding.weight_pct
            group["assets"].append(holding.issuer)

    issuer_concentration = [
        _build_exposure_record("issuer", issuer, weight, DEFAULT_ISSUER_LIMIT)
        for issuer, weight in sorted(issuer_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    sector_concentration = [
        _build_exposure_record("sector", sector, weight, DEFAULT_SECTOR_LIMIT)
        for sector, weight in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    geography_concentration = [
        _build_exposure_record("geography", geography, weight, DEFAULT_GEOGRAPHY_LIMIT)
        for geography, weight in sorted(geography_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    correlation_flags: List[Dict[str, Any]] = []
    for group_name, group_summary in correlation_groups.items():
        if group_summary["count"] > 1:
            correlation_flags.append(
                {
                    "category": "correlation_cluster",
                    "group": group_name,
                    "count": group_summary["count"],
                    "weight_pct": round(group_summary["weight_pct"], 4),
                    "assets": group_summary["assets"],
                    "status": "FLAGGED" if group_summary["weight_pct"] > CORRELATION_THRESHOLD * 100 else "WATCH",
                }
            )

    return {
        "portfolio_id": portfolio.portfolio_id,
        "issuer_concentration": issuer_concentration,
        "sector_concentration": sector_concentration,
        "geography_concentration": geography_concentration,
        "correlation_flags": correlation_flags,
    }


def score_severity(exposures: Dict[str, Any]) -> Dict[str, Any]:
    breaches = [
        record for record in exposures["issuer_concentration"] + exposures["sector_concentration"] + exposures["geography_concentration"]
        if record["status"] == "BREACH"
    ]
    warnings = [
        record for record in exposures["issuer_concentration"] + exposures["sector_concentration"] + exposures["geography_concentration"]
        if record["status"] == "WARNING"
    ]
    flags = exposures.get("correlation_flags", [])

    if breaches:
        max_breach = max(breaches, key=lambda record: record["value_pct"] - record["limit_pct"])
        if len(breaches) >= 2 or max_breach["value_pct"] >= max_breach["limit_pct"] + 2:
            severity = "CRITICAL"
        else:
            severity = "HIGH"
    elif flags:
        severity = "MEDIUM"
    elif warnings:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    confidence = min(100.0, 50.0 + len(breaches) * 12.0 + len(warnings) * 6.0 + len(flags) * 4.0)
    rationale_items: List[str] = []
    if breaches:
        rationale_items.append(f"Detected {len(breaches)} breached exposure limit(s).")
    if flags:
        rationale_items.append(f"Flagged {len(flags)} correlation cluster(s) for review.")
    if warnings and not breaches:
        rationale_items.append(f"Found {len(warnings)} concentration warning(s) near threshold.")
    if not rationale_items:
        rationale_items.append("Portfolio appears within configured concentration and geography risk limits.")

    rationale = " ".join(rationale_items)

    return {
        "severity": severity,
        "confidence": round(confidence, 2),
        "rationale": rationale,
    }
