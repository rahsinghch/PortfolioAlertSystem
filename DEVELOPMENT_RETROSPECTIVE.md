# Development Retrospective

This document is a retrospective on how the Portfolio Risk Alert System was
actually built — through a series of prompts to an AI coding agent (Claude
Code), rather than hand-written from a spec up front. It's written for two
audiences: people learning from this repo as a case study in AI-assisted
development, and anyone who wants to rebuild something like it themselves.

It complements the other docs rather than repeating them:
- `PROJECT_PLAN.md` — the original hackathon plan (the *intended* design)
- `ARCHITECTURE.md` — the system *as built* (the technical result)
- `CLAUDE.md` — operating notes for an AI agent working in this repo
- `docs/usage.md` — how an end user runs and reads the app

This document is about the *process* that produced all of the above: what
worked, what didn't, what broke, and what to do differently next time.

## 1. What went well, prompt-by-prompt

The application was built through roughly a dozen prompts, each one a
complete, shippable unit of work. In order:

1. *"start the application"* — vague on purpose (no path, no framework
   named), but unambiguous on intent. Forced directory discovery first,
   which is exactly the right instinct: read the README before assuming
   anything about how to run unfamiliar code.
2. *"does this application support a UI for user?"* → *"Yes"* — a
   two-turn clarifying exchange that unblocked a decision (which of two
   entry points to launch) without over-explaining.
3. *"push this code in repo rahsinghch/PortfolioAlertSystem"* — a clear
   action, deliberately checked before executing (the target repo already
   had content, so blindly pushing/force-pushing would have been wrong).
4. *"Help us understand the risk in a better way using visual
   representation... Also add various ways of input... document these"* —
   a single prompt that bundled three deliverables (charts, multi-input UX,
   docs) as one coherent feature rather than three disconnected asks.
5. *"check if the application can be deployed to vercel"* — a diagnostic
   question, answered by actually attempting a build rather than reasoning
   about it abstractly. This is the single highest-value prompt in the
   whole session (see §5).
6. *"push and deploy to vercel"*, *"add token usage... and push"*,
   *"deploy this app in hugging face"*, *"...Once done, push"* — each a
   tight implement→verify→document→ship loop.

**What made these effective:**
- Every prompt had a clear verb (start, push, check, deploy, add) even when
  the object was underspecified — ambiguity in *what* is recoverable by
  investigation; ambiguity in *what to do* is not.
- Bundling "build X, document it, then push" into one prompt gave a clean
  definition of "done" — implementation without documentation or without a
  push wasn't actually finished.
- Trailing "push" as its own instruction correctly signaled the boundary
  between *build/verify* (safe, reversible, no confirmation needed) and
  *publish* (visible to others, worth a final gate).
- Iterative, additive prompts let the app grow the way real software
  actually grows — working end-to-end at every step, never a big-bang
  integration.

## 2. What could have been better, prompt-by-prompt

None of these are complaints — they're the difference between "worked, but
took a diagnostic detour" and "would have worked on the first try":

- **"push this code in repo X"** didn't say what to do if `X` already had
  content. It happened to be safe (a placeholder README + LICENSE), but
  that had to be discovered by cloning and inspecting it first. A prompt
  like *"repo X is fresh, just initialized — merge our code into it"*
  would have skipped that investigation.
- **"deploy this app in hugging face"** carried no account/budget context.
  The blocker (Hugging Face now requires a paid plan for any Python-backed
  Space) was only discovered mid-task, after a login flow and a naming
  decision had already happened. Front-loading constraints — *"deploy to
  HF if it's free; if it needs a paid tier, stop and tell me"* — would have
  saved the setup work that preceded the dead end.
- **Coverage wasn't specified numerically.** "Add various ways of input"
  and "sample portfolios" both required inventing a reasonable scope (four
  input methods; three samples spanning LOW/MEDIUM/CRITICAL) rather than
  being told the target. This worked out, but a prompt like *"give me one
  LOW, one MEDIUM, and one CRITICAL example"* removes the guesswork
  entirely and costs nothing extra to write.
- **Multi-part prompts didn't prioritize.** *"Check X, put Y, once done
  push"* is efficient, but doesn't say what "done" means if X fails
  partway (as HF deployment did). Stating the fallback — *"push whatever
  succeeds, tell me what didn't"* — makes partial failure unambiguous
  instead of a judgment call.

## 3. Challenges faced, and how they were resolved

These are the real problems hit during development, in the order they
came up, with the actual resolution:

| Challenge | Resolution |
|---|---|
| Vague starting point — no app name or path given | Listed the working directory, found the one candidate folder, read its `README.md` before running anything |
| The Bash tool's shell had no Python on `PATH`, only PowerShell did | Switched all Python/dev commands to PowerShell for the rest of the session instead of fighting the Bash environment |
| Encoding mismatches when POSTing JSON with special characters (en/em dashes) via PowerShell | Explicitly encoded request bodies as UTF-8 bytes before sending, instead of relying on PowerShell's default string handling |
| Two "data corruption" scares that turned out to be console-display artifacts, not real bugs | Verified suspicious characters with `ord()`/raw byte inspection in Python rather than trusting what the terminal rendered |
| Target GitHub repo wasn't empty (had a placeholder README + LICENSE) | `git init` locally, `git merge --allow-unrelated-histories`, resolved the one real conflict by keeping the fuller local README and inheriting the LICENSE |
| `requirements.txt` had two dependency versions that don't exist on PyPI (`anthropic==3.0.1`, `pydantic==2.10.8`) | Discovered only by attempting a **real** `vercel build`, not by inspection; confirmed with `pip index versions` and repinned to real releases |
| `streamlit` was listed as a dependency but never imported anywhere | Confirmed with `grep` before removing it — it was dead weight dragging in a broken `pillow` build |
| Local Windows build environment didn't match Vercel's real Linux servers (a very new local Python version had no prebuilt wheels for some packages) | Pinned an explicit `.python-version` to a broadly-supported release and validated against a **real cloud deployment**, not just the local build |
| Vercel's Python builder silently auto-generates a `pyproject.toml` from `requirements.txt` and prefers it on every later build, masking edits to `requirements.txt` | Caught by reading the exact build log line ("Using Python 3.14 from pyproject.toml"); fixed by deleting the generated file before every retry |
| Vercel's preview URL returned HTML instead of JSON | Recognized it as Vercel's own SSO gate (Deployment Protection) by inspecting the response body, not assumed to be an app bug; verified against the production URL instead |
| A routine `vercel whoami` auth check silently triggered a real OAuth login | Caught immediately in the tool output, flagged transparently rather than continuing silently |
| Hugging Face Spaces required a paid PRO plan for any Python-backed Space | Recognized as a real external account/billing constraint outside the agent's control; stopped and handed the decision back rather than searching for a workaround |
| Changing `generate_rationale`'s return type (string → dict) risked breaking every caller silently | Grepped every call site and test first, then updated all of them in the same change |
| New CSV sample files crashed with a Pydantic `ValidationError` on blank optional cells (e.g. an empty `correlation_group`) | Traced to pandas' newer native string dtype: a blank cell isn't Python `None` or `NaN` the way `object`-dtype columns give you — it's the dtype's own NA marker, which survived a first `.where(pd.notnull(df), None)` attempt and only actually converted to `None` after explicitly casting to `object` dtype first. Caught by testing the new sample files against the real pipeline before wiring them into the UI, not just adding them and assuming they'd work |

## 4. What this project teaches, and the concepts behind it

**Architecture**
- *One pipeline, many front ends.* `analyze_portfolio()` is the single
  source of truth; the FastAPI API and the Gradio UI are both thin
  adapters over it. Adding a fifth way to bring in data never means
  duplicating analysis logic.
- *Graceful degradation over hard failures.* The Claude rationale call and
  every notification adapter (Slack/webhook/email) fail soft with a
  fallback instead of raising — the core feature works with zero
  configuration, which is also what makes the test suite and samples
  reliable without secrets.

**Data handling**
- *Tolerant normalization.* Accepting JSON, CSV, and a hand-edited table
  as three shapes of the same underlying schema, reconciled through one
  normalization function, rather than writing three schemas.
- *Domain-specific risk modeling.* Issuer/sector/geography concentration
  limits, WARNING-before-BREACH thresholds, and correlated-cluster
  detection are a general "diversification check" pattern, not a
  finance-only idea.

**Visualization**
- *Status-driven color, not identity-driven color.* Every chart colors
  bars by risk status (OK/WARNING/BREACH/...), not by which issuer or
  sector it is — so the same color always means the same thing everywhere
  in the app. Colors were chosen from a colorblind-safety-validated
  palette, not picked by eye.

**Software delivery**
- *A pinned version is a claim, not a fact.* Two dependency pins in this
  project didn't exist on PyPI at all, and were only caught by actually
  attempting an install. Trust `pip index versions` (or a lockfile) over
  a `requirements.txt` that "looks right."
- *Local ≠ target.* A build succeeding on a developer's machine doesn't
  mean it succeeds where it's actually deployed — different OS, different
  Python version, different available wheels. When in doubt, validate on
  the real target.
- *Automated tests and driving the live app are different safety nets.*
  Unit tests catch logic regressions; only curling the running server or
  driving the Gradio UI through `gradio_client` catches integration bugs,
  environment drift, and "it built but doesn't actually work."
- *AI-assisted, agentic development itself.* This whole app was built by
  describing outcomes ("add charts," "check if this deploys") to an
  agent that reads code, runs commands, and verifies its own work —
  rather than by writing every line by hand. The prompts in §1 are the
  actual "source code" of the development process.

## 5. Debugging techniques used

In rough order of how often they mattered:

1. **Read the real file before claiming anything about it.** Every fix in
   this project started with reading the actual current source, not
   assuming from memory or from what a doc claimed.
2. **Grep before you change a contract.** Before changing what a function
   returns, or removing a dependency, search for every place it's used.
   This is what made the `generate_rationale` return-type change and the
   `streamlit`/`anthropic` removals safe.
3. **Reproduce the smallest possible check.** `pip index versions
   <package>` to confirm a version really exists, rather than re-running
   the whole build and guessing at the cause from a wall of text.
4. **Don't trust a local pass as a global pass.** A build failure (or
   success) on one machine's OS/Python combination was explicitly treated
   as provisional until validated against the actual deployment target.
5. **Read the full log line, not the summary.** The stale `pyproject.toml`
   bug was visible only in one specific log line ("Using Python 3.14 from
   pyproject.toml") buried in a much longer build log — skimming past it
   would have led to repeating the same fix indefinitely.
6. **Verify characters at the byte/codepoint level when text looks wrong.**
   Two separate "this looks corrupted" moments were resolved with
   `ord()`/raw byte inspection, both turning out to be console rendering,
   not real bugs — cheap to check, easy to get wrong by eye.
7. **Don't trust a 200 status code alone.** A preview deployment returned
   HTTP 200 with an HTML login page instead of the expected JSON; the
   content was inspected, not just the status code.
8. **Drive the real thing, not just its internals.** `curl`/
   `Invoke-WebRequest` against a running server, and `gradio_client`
   against a running Gradio app, were used throughout as an outer loop
   around unit tests — proving the *feature* works, not just the function.
9. **Change one variable per retry.** Dependency fixes were applied one at
   a time (fix one bad pin → rebuild → fix the next) so each build's
   result was attributable to exactly one change.

## 6. The one prompt that could have built this application

No single prompt could have caught the environment-specific bugs (the bad
PyPI pins, the stale `pyproject.toml`, Vercel's protection gate, the
Hugging Face billing wall) — those were only discoverable by actually
attempting the work. But a well-specified opening prompt could have
produced the *entire feature set* in far fewer round trips:

> Build a Portfolio Risk Alert System: ingest portfolio holdings (JSON,
> CSV upload, and a manual entry table), normalize them into a common
> schema, and score concentration risk against configurable issuer/sector/
> geography limits plus correlated-asset-cluster detection, producing a
> LOW/MEDIUM/HIGH/CRITICAL severity with a confidence score. Generate a
> human-readable rationale via the Claude API, with a rule-based fallback
> and reported token usage when no API key is configured; escalate HIGH/
> CRITICAL alerts through Slack/webhook/email adapters that no-op cleanly
> when unconfigured, and keep an audit trail. Expose this through both a
> FastAPI service and a Gradio UI that share one analysis function — the
> UI should offer all input methods above plus a few built-in sample
> portfolios (spanning LOW through CRITICAL, each with a plain-language
> description of its risk profile and a downloadable CSV/JSON template),
> render concentration and correlation risk as colorblind-safe,
> status-colored bar charts, and include a short in-app legend explaining
> the severity levels and risk limits so a first-time user doesn't need
> external docs. Cover every module with tests, verify the deployed
> targets actually respond correctly (don't just trust that a build
> succeeded), and document the architecture, usage, and any AI-agent-
> specific operating notes. Push to GitHub repo `<owner>/<name>`, and
> deploy to Vercel — validate real dependency versions against PyPI rather
> than trusting `requirements.txt` as written, and confirm on the actual
> target platform, not just a local build.

Compare this to what was actually sent across the session (§1) — most of
the gap between "one prompt" and "a dozen prompts" is exactly the
diagnostic work in §3 that no prompt could have skipped, plus the natural
value of seeing each piece work before asking for the next.

## 7. A strategy to build this project again

A phased rebuild order that avoids most of the detours in §3:

1. **Model the domain first, with no I/O.** Write the Pydantic schema
   (`Holding`, `Portfolio`) and the pure scoring functions (exposure
   calculation, severity classification) with unit tests before any API,
   UI, or AI integration exists. This is the part least likely to change
   later and the easiest to get definitively correct early.
2. **Normalize before you integrate.** Build the raw-dict → canonical
   schema converter, tolerant of alternate field names and missing
   weights, and test it against messy/incomplete input on purpose.
3. **Get one front end fully working with zero external configuration.**
   Pick either the API or the UI, wire it to the scoring pipeline, and
   make sure it produces a complete, correct result with no `.env` file
   at all — this forces every fallback path (no AI key, no notification
   config) to exist from day one instead of being bolted on later.
4. **Add the AI rationale step with a graceful fallback**, so the pipeline
   never depends on an external API succeeding.
5. **Add escalation/notifications the same way** — each adapter
   independently optional, reporting its own skip/success/failure.
6. **Add the second front end as a thin adapter**, not a second
   implementation — if you're duplicating logic between the API and UI,
   extract it to a shared module first.
7. **Add visualization** once there's real data flowing: pick chart types
   by the question they answer (concentration vs. limit → bars, not a
   pie), assign color by status/meaning, and validate the palette rather
   than eyeballing it.
8. **Add every input method behind the one existing analysis function** —
   file upload and manual entry should both end up building the same raw
   dict shape that the first front end already consumes.
9. **Before deploying anywhere:** verify every pinned dependency version
   actually exists (`pip index versions`), remove anything unused
   (`grep` for its import), and pin an explicit, broadly-supported runtime
   version. Then validate on the **real target platform** — a local build
   passing is necessary, not sufficient.
10. **Add the onboarding/UX layer last**, once the core works: sample
    data with descriptions, downloadable templates, and an in-app legend
    explaining the domain — these are cheap to add once the underlying
    data model is stable, and expensive to retrofit if the schema is
    still moving.
11. **Write the architecture and agent-operating docs after the system
    stabilizes**, not before — documenting a design that's still changing
    just means rewriting the docs.

Each phase should end in a state that actually runs and is actually
tested — end-to-end, not just unit-tested — before moving to the next.
That discipline, more than any single prompt, is what kept this project
shippable at every step.
