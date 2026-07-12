# Project Plan: Portfolio Risk Alert System

## 1. Objective
Build a Python-hosted system that ingests portfolio holdings, applies Anthropic Claude-powered concentration and exposure analysis, scores breach severity, generates rationale, and triggers automated escalation actions.

This plan is based on the Hackathon problem statement in `Problem Statement Hackathon 4 Series.pdf`.

## 2. Requirements from the problem statement
- Portfolio Data Ingestion: Accept holdings and positions across equities, bonds, derivatives, and cash.
- Normalization: Standardize and normalize inputs for analysis across multiple accounts or funds.
- AI Concentration & Exposure Analysis: Use Claude to evaluate concentration limits for issuer, sector, geography, asset class, and correlation/volatility signals.
- Risk Severity Scoring: Output structured alert verdicts: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`, with a confidence score.
- Rationale Generation: Claude must generate a human-readable explanation for each alert.
- Automated Escalation & Notifications: Trigger downstream actions, such as Slack notifications, Jira tickets, audit entry updates, or dashboard flags.
- Audit Trail: Maintain a complete record of inputs, alerts, and actions.

## 3. Core architecture

### 3.1 Layers
- `data`: Ingestion and normalization
- `ai`: Claude prompt generation and API calls
- `analysis`: Risk scoring, limit detection, severity classification
- `notification`: Alert escalation and stakeholder notification
- `service`: API and UI surface for deployment

### 3.2 Proposed module breakdown
- `src/data_loader.py` — input ingestion from JSON/CSV and batch feeds
- `src/normalizer.py` — portfolio normalization and schema enforcement, including converting an uploaded CSV or manually edited table into the canonical schema
- `src/ai_client.py` — Anthropic Claude wrapper and prompt handling
- `src/risk_engine.py` — limit breach detection, severity scoring, correlation checks
- `src/visualization.py` — chart-ready DataFrames for concentration and correlation risk, colored by status
- `src/notifier.py` — downstream actions and audit trail logic
- `src/config.py` — environment variables and runtime config
- `src/app.py` — Hugging Face / local application entrypoint (multi-tab Gradio UI: paste JSON, file upload, manual entry, sample picker)
- `api/app.py` — Vercel-friendly API entrypoint (JSON body, file upload, and sample endpoints)
- `docs/prompts.md` — prompt design for Claude
- `docs/usage.md` — input methods and chart-reading guide
- `tests/` — unit tests for each layer

## 4. Folder structure

```
application/
  README.md
  PROJECT_PLAN.md
  requirements.txt
  vercel.json
  api/
    app.py
  docs/
    prompts.md
    usage.md
  src/
    app.py
    config.py
    ai_client.py
    data_loader.py
    normalizer.py
    risk_engine.py
    visualization.py
    notifier.py
    models.py
  data/
    sample_portfolio.json
    sample_portfolio_moderate.json
    sample_portfolio_diversified.json
    schema.json
  tests/
    test_data_loader.py
    test_risk_engine.py
    test_ai_client.py
    test_notifier.py
    test_normalizer.py
    test_visualization.py
    test_api.py
  Problem Statement Hackathon 4 Series.pdf
```

## 5. Implementation plan

### 5.1 Phase 1 — Data ingestion and normalization
- Build a JSON/CSV loader that accepts portfolio holdings from batch or stream.
- Normalize fields to a canonical schema: portfolio ID, fund, asset type, issuer, sector, geography, market value, weight, volatility.
- Validate data consistency and fill missing fields.

### 5.2 Phase 2 — Core risk and concentration logic
- Define configurable risk limits for issuer, sector, geography, asset class, and cluster correlation.
- Compute exposures and compare against the limits.
- Design scoring rules for breach severity and correlation clusters.

### 5.3 Phase 3 — Claude prompt design and API integration
- Build safe prompt templates in `docs/prompts.md`.
- Use the Anthropic Claude SDK to send structured prompts and receive JSON-friendly responses.
- Extract: breach type, severity label, confidence score, rationale, and suggested escalation actions.

### 5.4 Phase 4 — Alert generation and escalation
- Produce structured alert output with portfolio metadata, breach details, rationale, severity, and confidence.
- Implement notification adapters: Slack, email, Jira, or file-based audit trail.
- At minimum, simulate two automated actions for escalation.

### 5.5 Phase 5 — UI / demo and deployment
- Build a simple Hugging Face Space UI with Gradio or Streamlit.
- Build a Vercel-friendly API wrapper with FastAPI.
- Ensure the demo can ingest sample data, run analysis, and display results.
- Support multiple ways to bring in portfolio data — paste JSON, upload a `.json`/`.csv` file, edit a manual holdings table, or pick a built-in sample — so the same analysis path can be exercised without writing a payload by hand. See `docs/usage.md`.
- Visualize concentration and correlation risk as bar charts colored by breach status (OK/WARNING/BREACH/WATCH/FLAGGED), rather than only exposing severity as text, so risk drivers are visible at a glance.

### 5.6 Phase 6 — Testing and docs
- Add tests for normalization, Claude prompt creation, scoring logic, and alert generation.
- Document setup, usage, and deployment in README and plan docs.

## 6. Deployment strategy

### 6.1 Hugging Face Spaces
- Use `src/app.py` as the Space entrypoint.
- Add `requirements.txt` with Gradio and Anthropic.
- Deploy by connecting the repo to a new Hugging Face Space.
- The Space can run the Python app directly and expose a UI for portfolio upload.

### 6.2 Vercel
- Use `api/app.py` as the serverless endpoint.
- Add `vercel.json` with Python build instructions.
- Deploy using the Vercel CLI or by connecting the repository.
- Call `/analyze` with portfolio payloads from a frontend or postman.

## 7. Prompt engineering focus
- The quality of Claude responses is central.
- Use structured JSON prompts and clear instructions.
- Ensure prompts include example outputs and limit definitions.

## 8. Recommended next steps
1. Create the canonical portfolio schema in `data/schema.json`.
2. Implement ingestion and normalization first.
3. Build the Claude wrapper and a single analysis path.
4. Add alert escalation and a demo UI.
5. Deploy to Hugging Face Spaces first, then wire Vercel as an API fallback.
