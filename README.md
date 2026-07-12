# Portfolio Risk Alert System

A Python implementation of the Wissen Technology Hackathon 2026 portfolio risk and concentration alert system.

## What is included
- `PROJECT_PLAN.md`: Full implementation plan, architecture, task breakdown, and deployment guide.
- `docs/usage.md`: How to input portfolio data (paste JSON, file upload, manual entry, samples) and how to read the risk charts.
- `docs/prompts.md`: Claude prompt templates needed for concentration analysis, risk scoring, and escalation.
- `requirements.txt`: Python dependencies for FastAPI, Gradio, data processing, and Anthropic Claude.
- `api/app.py`: Vercel-ready FastAPI deployment skeleton.
- `src/`: Python source code for ingestion, normalization, risk scoring, AI rationale, notifications, and the Gradio UI.
- `src/visualization.py`: Builds the chart data behind the risk visualizations.
- `data/`: Sample portfolios covering critical, medium, and low risk profiles.

## Features
- **Concentration risk scoring** for issuer, sector, and geography limits, plus correlated-cluster detection, with `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` severity and an AI-generated rationale, reporting the Claude token usage (input/output/total) spent on each analysis.
- **Risk visualization** — bar charts for issuer/sector/geography concentration vs. their limits and for correlation cluster exposure, colored by status (OK/WARNING/BREACH/WATCH/FLAGGED) so severity is visible at a glance. See `docs/usage.md` for how to read them.
- **Four ways to bring in data**: paste JSON, upload a `.json`/`.csv` file (with downloadable templates in the UI), edit a manual holdings table, or load one of three built-in sample portfolios (each with an inline description of its risk profile). See `docs/usage.md` for details of each.
- **Built to be understood, not just used**: an in-app "How to read this analysis" panel explaining the risk limits and color legend, and a "Portfolio snapshot" line (holdings count, total value, largest position) so you can sanity-check what was actually analyzed.
- **Automated escalation**: Slack/webhook/email notification adapters and an audit trail entry per alert.

## Deployment targets
- Hugging Face Spaces: Use `src/app.py` with Gradio.
- Vercel: Use `api/app.py` with `vercel.json`.

## How to get started
1. Install dependencies: `python -m pip install -r requirements.txt`
2. Create `.env` with your Anthropic API key: `ANTHROPIC_API_KEY=your_key`
3. Run locally (from the `application/` directory):
   - FastAPI: `uvicorn api.app:app --reload` — see `http://127.0.0.1:8000/docs` for interactive API docs.
   - Gradio: `python -m src.app` — opens a browser UI at `http://127.0.0.1:7860`.
4. See `docs/usage.md` for the input methods and chart guide, and `PROJECT_PLAN.md` for the full architecture and deployment plan.
