# Roadmap and Known Limitations

This document is an honest gap analysis of the repo as it stands: features
that would be genuinely valuable but don't exist yet, and shortcomings in
what's already built. Everything here was checked against the actual
current code, not assumed — file/module references are given so each item
is actionable rather than vague.

This is a companion to `DEVELOPMENT_RETROSPECTIVE.md` (which covers *how*
the app was built) and `ARCHITECTURE.md` (which covers the system *as
built*). This document covers what's *missing or weak* in that system.

## Part 1 — Desirable features that don't exist yet

### Analysis depth
- **`volatility_30d` is captured but never analyzed.** `Holding` (`src/models.py`)
  and the normalizer both carry this field, and every sample/template
  includes it, but `risk_engine.py` never reads it — there's no
  volatility-based risk signal at all despite the data pipeline being
  built for one. The original plan (`PROJECT_PLAN.md` §2) explicitly calls
  for "correlation/volatility signals."
- **No asset-class concentration check.** The plan calls for handling
  "equities, bonds, derivatives, and cash," and `asset_type` is captured,
  but there's no limit or alert on asset-class concentration (e.g. "90% in
  derivatives") — only issuer/sector/geography/correlation are scored.
- **No multi-currency support.** `market_value` is a bare number with no
  currency field; a fund with mixed-currency holdings would have its
  weights computed as if everything were the same currency.
- **No batch or cross-portfolio analysis.** Every input path analyzes
  exactly one portfolio. The plan mentions normalizing "across multiple
  accounts or funds," but there's no way to compare or aggregate several
  portfolios in one request.
- **Exposure/severity scoring is 100% rule-based, not AI-driven.** The
  original plan's vision was Claude evaluating concentration limits
  directly; what's actually built uses Claude only to phrase the
  rationale text after the fact — the scoring itself (`risk_engine.py`) is
  plain Python thresholds. This is arguably a *safer* design (deterministic,
  testable, no hallucination risk in the actual severity number), but it's
  a real scope gap versus the original plan and worth being explicit about.

### Persistence and history
- **The audit trail isn't actually persisted.** `notifier.record_audit_entry`
  returns a dict describing what was found — it never writes to a file,
  database, or external system. Nothing survives past the single request/
  response. The plan calls for "a complete record of inputs, alerts, and
  actions," which doesn't exist today.
- **No historical/trend view.** `as_of` timestamps are captured but never
  compared across runs — there's no way to see "this fund's risk over the
  last 90 days" even though the data model has the timestamp for it.
- **No database at all.** Every analysis is stateless and in-memory; there
  is no persistence layer of any kind.

### Security and operations
- **The public API has no authentication.** `api/app.py` is deployed live
  on Vercel with zero auth — anyone with the URL can POST arbitrary
  portfolio data or hit any endpoint. For a tool meant to handle real fund
  holdings, this is a meaningful gap once it's live outside a local demo.
- **No rate limiting or request size limits.** `/analyze/upload` accepts
  any file size with no cap, on a public serverless endpoint.
- **No structured logging or observability.** There isn't a single
  `logging` call anywhere in `src/`. If a deployed instance misbehaves,
  there's no log trail to diagnose it from — only what a client happens to
  see in the response.
- **No CORS configuration.** A browser-based frontend hosted on a
  different origin couldn't call this API directly; there's no
  `CORSMiddleware` set up in `api/app.py`.
- **No CI pipeline.** There's no GitHub Actions workflow (or equivalent)
  running `pytest` on push or PR. Combined with Vercel's auto-deploy-on-push,
  a broken commit could reach production with nothing catching it first.
- **No documented way to set secrets on the deployed targets.** The docs
  cover creating a local `.env`, but not how to add `ANTHROPIC_API_KEY` (or
  the Slack/webhook/email vars) to the live Vercel project — the current
  production deployment runs with none of them set.

### UX and accessibility
- **No table/text alternative to the bar charts.** The visualization work
  followed a colorblind-safety-validated palette, but skipped the
  accompanying "a table view exists" accessibility guidance — someone who
  can't parse the charts at all (screen reader, print, etc.) has no
  equivalent way to read the same data.
- **Dark mode was never validated.** The chart palette was checked against
  the light chart surface only.
- **No export/download of a finished analysis.** Results are visible in
  the UI (`gr.JSON`, severity summary, charts) but there's no "download
  this as a PDF/CSV report" option.
- **Risk limits aren't adjustable from the UI.** Issuer/sector/geography/
  correlation thresholds are `.env`-only; a user can't interactively try
  "what if the issuer limit were 10% instead of 8%" without redeploying.
- **No handling for very large portfolios.** Nothing groups small holdings
  into "Other" or paginates — a portfolio with hundreds of issuers would
  produce an unreadable bar chart with one bar per issuer.

### API maturity
- **`PortfolioPayload.holdings` is typed as a bare `list`, not a list of a
  holding model.** FastAPI/Pydantic never validates individual holding
  shape at the API boundary — malformed holdings only fail deep inside
  `normalize_portfolio`, with a much less precise error (see Part 2 below,
  this also causes an actual bug, not just weak typing).
- **No `response_model` on any endpoint.** Every route returns `Any`, so
  the auto-generated `/docs` can't show a real response schema.
- **No API versioning** (e.g. `/v1/analyze`) — no compatibility story if
  the response shape changes later.

### Deployment completeness
- **Hugging Face deployment was never completed.** It's blocked by HF now
  requiring a paid plan for any Python-backed Space (a real account
  constraint, not a code issue — see `DEVELOPMENT_RETROSPECTIVE.md` §3).
  `README.md` still lists it as a deployment target as if proven; it isn't
  yet.
- **No dependency lock file.** Only top-level pins exist in
  `requirements.txt` — transitive dependencies aren't pinned, so a build
  today isn't guaranteed to reproduce identically in the future.

## Part 2 — Shortcomings in the current repo

These are concrete defects or weaknesses in what already exists, not
missing features:

1. **`/analyze` and `/analyze/upload` return an unhandled 500 on bad
   input**, instead of a clean 4xx. Neither route in `api/app.py` wraps the
   call to `analyze_portfolio_workflow` in a `try/except` — if
   `normalize_portfolio` raises `ValueError` (e.g. missing `portfolio_id`,
   empty `holdings`), that exception propagates unhandled and FastAPI
   returns a generic 500 Internal Server Error. This is a real, reproducible
   bug: `POST /analyze` with `{"portfolio_id": "", "fund": "F", "holdings": []}`
   fails with a 500 instead of a validation error explaining what's wrong.
2. **`AlertResult` in `src/models.py` is dead code.** It's defined but
   never instantiated anywhere — `analyze_portfolio` builds and returns a
   plain dict instead. Either use it or remove it; right now it's
   documentation that lies about the actual response shape.
3. **`tests/test_sample.py` is a placeholder that tests nothing**
   (`def test_placeholder(): assert True`). It's been left in the suite
   since the original scaffold.
4. **No test covers `src/app.py`'s Gradio-specific logic directly.**
   `analyze_json_input`, `analyze_file_input`, `analyze_table_input`, and
   `analyze_sample_input` — including their error-handling branches (bad
   file type, missing file, bad sample name) — have no dedicated unit
   tests. They were verified manually via `gradio_client` during
   development, but that verification isn't part of the persisted,
   automated test suite.
5. **Root-level scratch scripts are committed alongside real application
   code.** `check_anthropic.py` and `extract_pdf_text.py` are ad hoc
   exploration scripts from early development, not part of the app, not
   imported by anything, and not documented as scratch files — a new
   contributor has no way to tell they're not load-bearing without reading
   them.
6. **`PROJECT_PLAN.md`'s folder structure section is stale.** It still
   lists `data/schema.json` and `tests/test_data_loader.py`, neither of
   which exists — the actual data/test files diverged from this plan
   without the plan being updated to match.
7. **The originally-planned `data/schema.json` was never created.**
   `PROJECT_PLAN.md` §8 lists "Create the canonical portfolio schema in
   `data/schema.json`" as the first recommended next step; the only schema
   that exists is implicit in the Pydantic models in `src/models.py`, which
   isn't published anywhere a non-Python integrator could read it.
8. **Broad `except Exception` in `ai_client.py` and `notifier.py` swallows
   programming bugs, not just expected external failures.** If `_build_prompt`
   or `_parse_response` had a bug, it would be silently reported as "Claude
   call failed, using rule-based fallback" — indistinguishable from an
   actual network failure. This is a deliberate robustness/observability
   tradeoff (see `DEVELOPMENT_RETROSPECTIVE.md` §4's note on graceful
   degradation), but it means a real bug in that code path could go
   unnoticed indefinitely without the logging gap above being fixed too.
9. **Dependency versions haven't been audited for security advisories.**
   The pins in `requirements.txt` (e.g. `fastapi==0.108.0`, `httpx==0.24.0`)
   are old relative to current releases; they were checked for *existing*
   (do they install at all — see `DEVELOPMENT_RETROSPECTIVE.md` §3) but not
   for known CVEs.
10. **The CSV template's weights don't sum to 100%.**
    `data/sample_holdings_template.csv` has four rows summing to 31%
    weight — fine mechanically (weights are used as given, not required to
    total 100), but a user downloading it as a starting point may be
    confused why the numbers don't add up, since the equivalent JSON
    samples do total ~100%.
11. **A portfolio with all-zero `market_value` and all-zero `weight_pct`
    produces a silent, misleadingly "safe" result.** `normalize_portfolio`
    only recomputes `weight_pct` from `market_value` when the total market
    value is positive; if both are left at zero (e.g. an incomplete
    upload), every holding reports 0% weight and the analysis comes back
    LOW severity — indistinguishable from a genuinely well-diversified
    portfolio. Nothing flags "this input looks incomplete."
12. **README.md lists Hugging Face as a supported deployment target**
    without qualification, even though that deployment was never actually
    completed (see Part 1). The doc should note this is unverified/blocked
    rather than implying parity with the working Vercel deployment.

## Suggested priority if picking this up

If someone wanted to work through this list, roughly highest-value first:
1. Fix the unhandled-500 bug (#1 in Part 2) — it's a real, user-facing defect.
2. Add authentication and request size limits to the public API (Part 1,
   Security) — the app is live on the public internet today with neither.
3. Add structured logging (Part 1, Security) — makes almost everything
   else on this list easier to diagnose once it exists.
4. Remove or use `AlertResult` and the root-level scratch scripts (#2, #5)
   — pure cleanup, no design decisions required.
5. Add tests for `src/app.py`'s Gradio wrappers and flesh out or delete
   `test_sample.py` (#3, #4) — closes the test-coverage gap cheaply.
6. Everything else in Part 1 is a genuine feature decision, not a fix, and
   should be prioritized against who's actually going to use this.
