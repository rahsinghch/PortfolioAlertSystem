# Portfolio Risk Alert System

A Python implementation plan for the Wissen Technology Hackathon 2026 portfolio risk and concentration alert system.

## What is included
- `PROJECT_PLAN.md`: Full implementation plan, architecture, task breakdown, and deployment guide.
- `docs/prompts.md`: Claude prompt templates needed for concentration analysis, risk scoring, and escalation.
- `requirements.txt`: Python dependencies for FastAPI, Gradio, data processing, and Anthropic Claude.
- `api/app.py`: Vercel-ready FastAPI deployment skeleton.
- `src/`: Python source code skeleton for ingestion, AI analysis, scoring, and notifications.

## Deployment targets
- Hugging Face Spaces: Use `src/app.py` with Gradio or Streamlit.
- Vercel: Use `api/app.py` with `vercel.json`.

## How to get started
1. Install dependencies: `python -m pip install -r requirements.txt`
2. Create `.env` with your Anthropic API key: `ANTHROPIC_API_KEY=your_key`
3. Run locally:
   - FastAPI: `uvicorn api.app:app --reload`
   - Gradio: `python src/app.py`
4. Follow `PROJECT_PLAN.md` to implement the core modules and deployment.
