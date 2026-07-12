# Usage Guide: Input Methods and Risk Visualization

This guide covers the two ways to run the Portfolio Risk Alert System
(Gradio UI and FastAPI), the four ways to bring in portfolio data, and
how to read the risk charts.

## Running it

- Gradio UI: `python -m src.app` (from the `application/` directory), then open `http://127.0.0.1:7860`.
- FastAPI: `uvicorn api.app:app --reload`, then open `http://127.0.0.1:8000/docs` for interactive Swagger docs.

## Ways to input portfolio data

### 1. Paste JSON
Gradio tab **"Paste JSON"**, or `POST /analyze` with a JSON body:

```json
{
  "portfolio_id": "PORT-001",
  "fund": "Example Fund",
  "as_of": "2026-07-12T00:00:00Z",
  "holdings": [
    {"issuer": "Issuer A", "asset_type": "Equity", "sector": "Energy", "geography": "India", "market_value": 9800000, "weight_pct": 9.8, "volatility_30d": 0.32, "correlation_group": "cluster-1"}
  ]
}
```

Use this when you already have a normalized payload (e.g. from an upstream system).

### 2. Upload a file (.json or .csv)
Gradio tab **"Upload File"**, or `POST /analyze/upload` (multipart form).

- `.json` files are read as a full portfolio payload, same shape as above.
- `.csv` files need one row per holding, with columns: `issuer, asset_type, sector, geography, market_value, weight_pct, volatility_30d, correlation_group`. Since a holdings CSV has no place for portfolio-level metadata, supply `portfolio_id`, `fund`, and (optionally) `as_of` as separate fields — form fields in the API, textboxes above the upload button in the UI.

Example API call:
```
curl -X POST http://127.0.0.1:8000/analyze/upload \
  -F "file=@holdings.csv" \
  -F "portfolio_id=CSV-001" \
  -F "fund=My Fund"
```

Use this for ad hoc files exported from a portfolio management system or spreadsheet.

### 3. Manual entry table
Gradio tab **"Manual Entry"** only (no direct API equivalent). An editable grid pre-filled with two example rows — add, edit, or delete rows directly, set the portfolio ID/fund name/as-of date, then click **Analyze Table**.

Use this to sanity-check a hypothetical or "what-if" holding mix without preparing a file first.

### 4. Sample portfolios
Gradio tab **"Sample Portfolios"** — a dropdown of three pre-built examples with different risk profiles, or via the API:

- `GET /samples` — lists the available sample names.
- `GET /samples/{sample_name}` — runs the analysis for that sample directly.

| Sample | Profile |
|---|---|
| Concentrated (Critical risk) | Two issuer breaches, one sector breach, a correlated cluster |
| Emerging markets (Medium risk) | Issuer/sector warnings near their limits, no breaches |
| Diversified (Low risk) | 15 holdings spread across issuers/sectors/geographies, everything within limits |

Use this to see how the severity, rationale, and charts change across risk levels without preparing your own data.

## Reading the risk charts

Every analysis (regardless of which input method produced it) renders four charts, in addition to the JSON result and a severity summary:

- **Issuer / Sector / Geography Concentration** — one bar per issuer, sector, or geography, height = portfolio weight %. Bars are colored by status, not by identity, so the color always means the same thing across every chart:
  - 🟢 green = **OK** (within limit)
  - 🟡 amber = **WARNING** (within 90% of the limit)
  - 🔴 red = **BREACH** (over the limit)
  - Hover a bar to see its exact weight % and configured limit %.
- **Correlation Cluster Exposure** — one bar per group of holdings flagged as correlated (same `correlation_group`, more than one holding), height = their combined weight %.
  - 🟠 orange = **WATCH** (correlated, under the flag threshold)
  - 🔴 red = **FLAGGED** (correlated and over the 85% correlation-weight threshold)

The severity summary above the charts uses the same color convention (🟢 LOW, 🟡 MEDIUM, 🟠 HIGH, 🔴 CRITICAL) so the headline severity and the chart-level detail always agree.

## Token usage

Every analysis result includes a `token_usage` field — `input_tokens`, `output_tokens`, and `total_tokens` — reported by the Claude call that generated the rationale. The severity summary shows the same figure as a "Tokens used" line. If `ANTHROPIC_API_KEY` isn't set (or the Claude call fails), no API call is made, the rationale falls back to a rule-based summary, and token usage reports as 0.
