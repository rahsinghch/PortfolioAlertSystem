# Architecture

This document describes the system as built. For the original hackathon
planning document (requirements, phased task breakdown, deployment strategy
rationale), see `PROJECT_PLAN.md`. For end-user instructions, see
`README.md` and `docs/usage.md`.

## System overview

The Portfolio Risk Alert System ingests a portfolio's holdings, evaluates
issuer/sector/geography concentration and correlated-asset-cluster risk
against configurable limits, scores an overall severity, generates a
human-readable rationale (via Claude, with a rule-based fallback), and
triggers downstream escalation (Slack/webhook/email/audit log). Results are
surfaced through two independent front ends that share one analysis
pipeline.

## Data flow

```
                     ┌───────────────────────────┐
Paste JSON ────────▶ │                           │
Upload .json/.csv ──▶│   raw portfolio dict      │
Manual entry table ─▶│  (portfolio_id, fund,     │
Sample picker ──────▶│   as_of, holdings[])      │
                     └─────────────┬─────────────┘
                                   ▼
                     normalizer.normalize_portfolio()
                     - resolves field-name aliases
                     - fills weight_pct from market_value if missing
                                   ▼
                     risk_engine.evaluate_exposures()
                     - issuer / sector / geography weight totals vs. limits
                     - correlation cluster detection
                                   ▼
                     risk_engine.score_severity()
                     - LOW / MEDIUM / HIGH / CRITICAL + confidence
                                   ▼
                     ai_client.generate_rationale()
                     - Claude call, or rule-based text if no API key/failure
                                   ▼
                     notifier.build_alert_actions() / record_audit_entry()
                     / send_notifications()
                     - Slack, webhook, email adapters (each "skipped" if
                       unconfigured, never fails the request)
                                   ▼
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
              api/app.py (JSON)        src/app.py (Gradio UI)
                                                   │
                                                   ▼
                                     visualization.build_charts()
                                     - status-colored concentration &
                                       correlation bar charts
```

Every input path (paste JSON, file upload, manual table, sample picker)
converges on the same `analyze_portfolio(raw_dict)` function in
`src/app.py` — there is exactly one analysis code path, not one per input
method.

## Components

| Module | Responsibility |
|---|---|
| `src/data_loader.py` | Read a portfolio from a `.json` file or a holdings `.csv` into memory. |
| `src/normalizer.py` | Convert a raw dict (or a holdings DataFrame, via `dataframe_to_raw_portfolio`) into the canonical `Portfolio`/`Holding` models; tolerates alternate field names and missing weights. |
| `src/models.py` | Pydantic schema: `Holding`, `Portfolio`, `AlertAction`, `AlertResult`. |
| `src/risk_engine.py` | Pure functions: `evaluate_exposures` (concentration + correlation math) and `score_severity` (severity/confidence/rationale-summary rules). No I/O. |
| `src/ai_client.py` | Builds the Claude prompt from exposures, calls the Anthropic Messages API, parses the response. Falls back to a templated string on missing key or any failure — never raises. |
| `src/notifier.py` | Builds escalation actions from severity, records an audit entry, and fires Slack/webhook/email notifications (each independently optional via `config.py`). |
| `src/visualization.py` | Turns exposure/correlation records into chart-ready `pandas.DataFrame`s and defines the fixed status/severity color palettes used everywhere in the UI. |
| `src/config.py` | All environment-driven configuration (risk limits, Anthropic settings, notification adapter credentials), loaded from `.env`. |
| `src/app.py` | Core pipeline (`analyze_portfolio`) plus the Gradio UI (`build_demo`) with four input tabs. |
| `api/app.py` | FastAPI service exposing `/analyze` (JSON body), `/analyze/upload` (file), `/samples` and `/samples/{name}`. Delegates all analysis to `src.app.analyze_portfolio`. |
| `data/*.json` | Three sample portfolios spanning CRITICAL, MEDIUM, and LOW severity, used by the sample picker in both front ends. |

## Design decisions

- **Graceful degradation over hard failures.** The AI rationale step and every notification adapter are individually optional; the pipeline always returns a complete result even with zero configuration (no `.env` at all). This is why the sample portfolios and test suite work out of the box.
- **Normalization tolerates messy input on purpose.** Because the system accepts hand-typed JSON, uploaded CSVs, and manually edited tables, `normalize_portfolio` resolves common field-name variants and derives `weight_pct` from `market_value` when absent, instead of rejecting anything that isn't already canonical.
- **One pipeline, many front doors.** `api/app.py` and the Gradio UI never duplicate analysis logic — both call `src.app.analyze_portfolio`. Adding a fifth input method (e.g. a batch endpoint) should mean writing a new adapter that produces a raw dict, not new analysis code.
- **Color means one thing everywhere.** `visualization.STATUS_COLORS`/`SEVERITY_COLORS` are defined once and reused by every chart and the severity summary, so a color never has to be re-learned per chart.

## Deployment targets

- **Vercel** — `api/app.py` as a serverless FastAPI endpoint, configured via `vercel.json`.
- **Hugging Face Spaces** — `src/app.py` as the Gradio Space entrypoint.

## Testing

`tests/` mirrors the module layout (`test_risk_engine.py`, `test_normalizer.py`, `test_visualization.py`, `test_ai_client.py`, `test_notifier.py`, `test_api.py`). API tests use FastAPI's `TestClient` against `api.app.app` directly — no network calls, no running server required.
