from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict

from src.app import analyze_portfolio as analyze_portfolio_workflow

class PortfolioPayload(BaseModel):
    portfolio_id: str
    fund: str
    holdings: list
    as_of: str | None = None

app = FastAPI(title="Portfolio Risk Alert API")

@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "Portfolio Risk Alert API is running"}

@app.post("/analyze")
async def analyze_portfolio(payload: PortfolioPayload) -> Any:
    raw_payload = payload.model_dump()
    return analyze_portfolio_workflow(raw_payload)
