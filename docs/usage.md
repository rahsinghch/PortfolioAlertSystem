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
- Not sure where to start? The Gradio tab has four download links — three CSVs (a starter template, a diversified/LOW-risk example, and a concentrated/CRITICAL-risk example) and a full JSON example — download one, edit it, and upload it back. See the table in `data/` below for what's in each.

Example API call:
```
curl -X POST http://127.0.0.1:8000/analyze/upload \
  -F "file=@holdings.csv" \
  -F "portfolio_id=CSV-001" \
  -F "fund=My Fund"
```

Use this for ad hoc files exported from a portfolio management system or spreadsheet.

### 3. Manual entry table
Gradio tab **"Manual Entry"** only (no direct API equivalent). An editable grid pre-filled with two example rows — add, edit, or delete rows directly, set the portfolio ID/fund name/as-of date, then click **Analyze Table**. `weight_pct` can be left at 0 to auto-compute from `market_value`; `correlation_group` is optional.

Use this to sanity-check a hypothetical or "what-if" holding mix without preparing a file first.

### 4. Sample portfolios
Gradio tab **"Sample Portfolios"** — a dropdown of five pre-built examples covering every severity level (selecting one shows a description of what makes it that risk level, before you even run the analysis), or via the API:

- `GET /samples` — lists the available samples, each with a `name` and a `description` of its risk profile.
- `GET /samples/{sample_name}` — runs the analysis for that sample directly.

| Sample (JSON) | Severity | Profile |
|---|---|---|
| Concentrated (Critical risk) | CRITICAL | Two issuer breaches, one sector breach, a correlated cluster |
| Geography concentration (High risk) | HIGH | One geography (India) just over its 70% limit — every issuer and sector is clean; the only breach is a single one, one notch below CRITICAL |
| Emerging markets (Medium risk) | MEDIUM | Issuer/sector warnings near their limits (not breaches), plus a correlated cluster below the flag threshold (WATCH) |
| Correlation cluster flagged (Medium risk) | MEDIUM | 12 holdings sharing one correlation group total 85.8% combined weight — over the flag threshold (FLAGGED, not WATCH) — while every issuer/sector/geography is individually clean. Shows that a chart can flag red even when overall severity is only MEDIUM |
| Diversified (Low risk) | LOW | 15 holdings spread across issuers/sectors/geographies, everything within limits |

There are also three downloadable **CSV** samples in the Upload File tab — a starter template, a diversified/LOW-risk example (`data/sample_holdings_diversified.csv`), and a concentrated/CRITICAL-risk example (`data/sample_holdings_concentrated.csv`) — for trying the CSV path with known-good data instead of only JSON.

Use this to see how the severity, rationale, and charts change across risk levels without preparing your own data.

## Reading the risk charts

Every analysis (regardless of which input method produced it) renders six visuals, in addition to the JSON result and a severity summary:

- **Issuer / Sector / Geography Concentration** — one bar per issuer, sector, or geography, height = portfolio weight %. Bars are colored by status, not by identity, so the color always means the same thing across every chart:
  - 🟢 green = **OK** (within limit)
  - 🟡 amber = **WARNING** (within 90% of the limit)
  - 🔴 red = **BREACH** (over the limit)
  - Hover a bar to see its exact weight % and configured limit %.
- **Correlation Cluster Exposure** — one bar per group of holdings flagged as correlated (same `correlation_group`, more than one holding), height = their combined weight %.
  - 🟠 orange = **WATCH** (correlated, under the flag threshold)
  - 🔴 red = **FLAGGED** (correlated and over the 85% correlation-weight threshold)
- **Portfolio Composition (by Asset Type)** — one bar per asset type (Equity/Bond/...), height = combined portfolio weight %. This one isn't status-colored — there's no configured limit on asset type today, so it's a plain view of where the money sits, not a breach check.
- **Holdings Detail** — a plain table listing every holding (issuer, asset type, sector, geography, weight %, market value), sorted by weight descending. It's the exact numbers behind every chart above, and a plain-data alternative for anyone who can't read the bar charts (screen reader, print, etc.).

The severity summary above the charts uses the same color convention (🟢 LOW, 🟡 MEDIUM, 🟠 HIGH, 🔴 CRITICAL) so the headline severity and the chart-level detail always agree.

The Gradio UI also has a collapsible **"How to read this analysis"** panel above the input tabs, showing the exact risk limits in effect (issuer/sector/geography/correlation thresholds, pulled live from configuration) and what each severity level and chart color means — so you don't need to leave the app to understand the result.

## Understanding the portfolio itself

Every severity summary includes a **"Portfolio snapshot"** line — holdings count, total market value, and the largest single position — so you can sanity-check what was actually analyzed (e.g. "did my CSV upload parse the number of rows I expected?") before digging into the risk charts. It's also available programmatically as the `portfolio_overview` field on every analysis result.

Every analysis result also includes a `holdings` field — every holding as normalized (after alternate field names are resolved and `weight_pct` is auto-computed if it was left at 0) — so you can confirm exactly how your input was interpreted, not just the aggregated risk numbers. This is what feeds the Portfolio Composition chart and Holdings Detail table above.

## Token usage

Every analysis result includes a `token_usage` field — `input_tokens`, `output_tokens`, and `total_tokens` — reported by the Claude call that generated the rationale. The severity summary shows the same figure as a "Tokens used" line. If `ANTHROPIC_API_KEY` isn't set (or the Claude call fails), no API call is made, the rationale falls back to a rule-based summary, and token usage reports as 0.
