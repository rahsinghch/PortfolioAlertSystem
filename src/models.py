"""Pydantic models for portfolio holdings and alert outputs."""

from pydantic import BaseModel
from typing import List, Optional

class Holding(BaseModel):
    issuer: str
    asset_type: str
    sector: str
    geography: str
    market_value: float
    weight_pct: float
    volatility_30d: Optional[float] = None
    correlation_group: Optional[str] = None

class Portfolio(BaseModel):
    portfolio_id: str
    fund: str
    as_of: Optional[str] = None
    holdings: List[Holding]

class AlertAction(BaseModel):
    type: str
    target: str
    message: str

class AlertResult(BaseModel):
    portfolio_id: str
    severity: str
    confidence: float
    rationale: str
    exposures: List[dict]
    actions: List[AlertAction]
    audit_notes: Optional[str] = None
