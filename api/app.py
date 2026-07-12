import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.app import SAMPLE_PORTFOLIOS, analyze_portfolio as analyze_portfolio_workflow
from src.data_loader import load_portfolio_json
from src.normalizer import dataframe_to_raw_portfolio


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


@app.post("/analyze/upload")
async def analyze_uploaded_file(
    file: UploadFile = File(...),
    portfolio_id: str = Form("UPLOAD-001"),
    fund: str = Form("Uploaded Fund"),
    as_of: Optional[str] = Form(None),
) -> Any:
    """Analyze a portfolio from an uploaded .json or .csv file.

    CSV uploads need one row per holding; portfolio_id/fund/as_of are
    supplied as separate form fields since a holdings CSV has no
    portfolio-level metadata columns.
    """
    suffix = Path(file.filename or "").suffix.lower()
    contents = await file.read()

    if suffix == ".json":
        raw = json.loads(contents.decode("utf-8"))
    elif suffix == ".csv":
        holdings_df = pd.read_csv(io.BytesIO(contents))
        raw = dataframe_to_raw_portfolio(holdings_df, portfolio_id, fund, as_of)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a .json or .csv file.")

    return analyze_portfolio_workflow(raw)


@app.get("/samples")
async def list_samples() -> Dict[str, List[str]]:
    return {"samples": list(SAMPLE_PORTFOLIOS.keys())}


@app.get("/samples/{sample_name}")
async def analyze_sample(sample_name: str) -> Any:
    if sample_name not in SAMPLE_PORTFOLIOS:
        raise HTTPException(status_code=404, detail=f"Unknown sample '{sample_name}'. See GET /samples for valid names.")
    raw = load_portfolio_json(SAMPLE_PORTFOLIOS[sample_name])
    return analyze_portfolio_workflow(raw)
