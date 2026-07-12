# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install dependencies:
```
python -m pip install -r requirements.txt
```

Run the FastAPI service (from this directory):
```
uvicorn api.app:app --reload
```
Interactive docs at `http://127.0.0.1:8000/docs`.

Run the Gradio UI (from this directory) — **must** be run as a module, not `python src/app.py`, because `src/app.py` uses relative imports (`from .config import ...`):
```
python -m src.app
```
Opens a browser UI at `http://127.0.0.1:7860`.

Run all tests:
```
python -m pytest
```

Run a single test file or test:
```
python -m pytest tests/test_risk_engine.py
python -m pytest tests/test_risk_engine.py::test_evaluate_exposures_and_score_severity
```

There is no configured linter or build step in this repo (no `pyproject.toml`/`setup.cfg`/lint config) — don't invent one.

## Architecture

### One pipeline, two front ends
`api/app.py` (FastAPI) and `src/app.py` (Gradio) are both thin front ends over the same core pipeline, defined by `analyze_portfolio()` in `src/app.py`:

```
raw dict → normalizer.normalize_portfolio → risk_engine.evaluate_exposures → risk_engine.score_severity
         → ai_client.generate_rationale → notifier.build_alert_actions/record_audit_entry/send_notifications
```

`api/app.py` imports `analyze_portfolio` directly from `src.app` — any change to the pipeline's return shape affects both front ends. Deployment targets follow the front end: Vercel serves `api/app.py` (`vercel.json`), Hugging Face Spaces serves `src/app.py` (Gradio).

### Four input paths converge on one function
The Gradio UI (`src/app.py`) exposes four tabs — paste JSON, file upload (`.json`/`.csv`), a manual holdings table, and a sample picker (`data/*.json`) — each with its own `analyze_*_input` wrapper, but all of them ultimately build a raw portfolio dict and call the same `analyze_portfolio()`. CSV/manual-table input goes through `normalizer.dataframe_to_raw_portfolio()` first, since a holdings table has no place for portfolio-level metadata (`portfolio_id`/`fund`/`as_of` are supplied separately). `api/app.py` mirrors this with `/analyze` (JSON body), `/analyze/upload` (file), and `/samples`/`/samples/{name}`.

### Normalization is deliberately forgiving
`normalizer.normalize_portfolio()` accepts multiple field-name aliases per input (`weight_pct`/`weight`, `geography`/`country`, `portfolio_id`/`portfolioId`, etc.) and recomputes `weight_pct` from `market_value` when the caller didn't supply it. This is what lets ad hoc CSVs and hand-edited tables work without a strict schema.

### Risk scoring thresholds live in `risk_engine.py` + `config.py`
Limits (`DEFAULT_ISSUER_LIMIT`, `DEFAULT_SECTOR_LIMIT`, `DEFAULT_GEOGRAPHY_LIMIT`, `CORRELATION_THRESHOLD`) are env-configurable in `config.py`. `risk_engine._classify_status` marks a value `WARNING` at ≥90% of its limit and `BREACH` over it. `score_severity` escalates to `CRITICAL` when there are ≥2 breaches, or a single breach ≥2 points over its limit; a single smaller breach is `HIGH`; correlation flags or warnings alone (no breach) are `MEDIUM`; otherwise `LOW`.

### Everything downstream degrades gracefully without config
`ai_client.generate_rationale` falls back to a templated rule-based rationale if `ANTHROPIC_API_KEY` is unset or the API call fails — it never raises. `notifier.send_notifications` returns a `"skipped"` status per adapter (Slack/webhook/email) when the corresponding env var isn't set, rather than failing the whole analysis. This means the full pipeline runs end-to-end with zero configuration; tests and samples rely on this.

### Token usage travels with the rationale, not separately
`generate_rationale` returns `{"rationale": str, "token_usage": {"input_tokens", "output_tokens", "total_tokens"}}` in one call — both come from the same Claude API response, so they're fetched together rather than requiring a second request. `token_usage` is all zeros whenever no API call was made (missing key or failed request). `analyze_portfolio` surfaces this as a top-level `token_usage` field, and the Gradio severity summary renders it as a "Tokens used" line.

### Visualization uses a fixed status palette, not per-chart colors
`src/visualization.py` builds the chart-ready DataFrames consumed by the Gradio `BarPlot`s, and defines `STATUS_COLORS` (OK/WARNING/BREACH/WATCH/FLAGGED) and `SEVERITY_COLORS` (LOW/MEDIUM/HIGH/CRITICAL) once, shared across every chart and the severity summary markdown — so a given status always renders the same color everywhere in the UI. `build_charts()` also returns `asset_allocation` (composition by asset type — no configured limit, so it's uncolored) and `holdings_table` (every holding, sorted by weight — the plain-data alternative to the bar charts), both built from `analyze_portfolio`'s `holdings` field rather than from `exposures`. See `docs/usage.md` for the full color legend.

### `dataframe_to_raw_portfolio` must cast to `object` dtype before filling blanks
A CSV/table column with some blank cells and some real values parses under pandas' native string dtype, where a blank cell is that dtype's own NA marker — `.where(pd.notnull(df), None)` alone does **not** turn it into Python `None` (it silently re-coerces back to the NA marker); you must `.astype(object)` first. This bit real CSV samples in this repo (see `DEVELOPMENT_RETROSPECTIVE.md` §3) — if you touch `normalizer.dataframe_to_raw_portfolio`, keep the `.astype(object)` cast, and test any new CSV fixture with a genuinely blank optional cell (not just an absent column) before trusting it.

### The UI explains itself instead of requiring the docs
`analyze_portfolio` also returns a `portfolio_overview` field (holdings count, total market value, largest position) derived from data already computed by `risk_engine.evaluate_exposures` — no extra pass over the holdings. The Gradio UI surfaces this, plus a config-driven "How to read this analysis" legend (`_how_to_read_markdown`) and per-sample descriptions (`SAMPLE_DESCRIPTIONS`), so a first-time user can understand a result without leaving the app. `SAMPLE_DESCRIPTIONS` is also reused by `api/app.py`'s `/samples` endpoint, so API consumers get the same descriptions.

### Docs split by audience
- `README.md` — quick start and feature overview.
- `docs/usage.md` — end-user guide to the four input methods and how to read the risk charts.
- `docs/prompts.md` — the Claude prompt templates/design notes for the AI rationale step.
- `PROJECT_PLAN.md` — the original hackathon implementation plan and architecture rationale; useful for *why* the module boundaries are what they are.
