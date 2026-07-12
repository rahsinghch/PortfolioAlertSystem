# Claude Prompt Templates for Portfolio Risk Alert System

This file captures the prompt patterns needed to implement the Claude-driven concentration and risk analysis.

## 1. System instruction

Use this system prompt in every Claude request to set the task context.

```
You are a risk analytics assistant. Analyze portfolio holdings for concentration breaches, sector and geography exposure, correlation clusters, and volatility risks. Produce structured output in JSON with labels, severity, confidence, and a human-readable rationale.
```

## 2. Portfolio normalization prompt

```
Analyze the raw portfolio record below and normalize it into canonical fields. Return only JSON.

Input:
{
  "portfolio_id": "PORT-2026-0442",
  "fund": "Alpha Growth Opportunities Fund",
  "holdings": [ ... ]
}

Output schema:
{
  "portfolio_id": string,
  "fund": string,
  "as_of": string,
  "holdings": [
    {
      "issuer": string,
      "asset_type": string,
      "sector": string,
      "geography": string,
      "market_value": number,
      "weight_pct": number,
      "volatility_30d": number,
      "correlation_group": string | null
    }
  ]
}
```

## 3. Concentration and exposure analysis prompt

```
Evaluate the portfolio holdings against the following configurable limits:
- single issuer limit: 8.0% of NAV
- sector limit: 25.0% of NAV
- geography limit: 70.0% of NAV
- correlation cluster flag: rolling 30-day correlation > 0.85

Return JSON describing each exposure check and whether the position is OK, WARNING, BREACH, or FLAGGED.
```

## 4. Severity scoring prompt

```
Based on the exposure analysis, classify the overall portfolio risk into one of: LOW, MEDIUM, HIGH, CRITICAL.
Provide a confidence score from 0 to 100 and a short rationale.

Output schema:
{
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "confidence": number,
  "rationale": string,
  "breach_summary": [
    { "type": string, "value": string, "limit": string, "status": string }
  ]
}
```

## 5. Alert rationalization prompt

```
Generate a clear explanation for the alert. Include the top three risk drivers, why each is important, and the next recommended action.
```

## 6. Escalation action prompt

```
Based on the severity label and breach context, recommend two specific downstream escalation actions for stakeholders.
Example actions: Slack alert to risk desk, Jira ticket creation, audit log entry, dashboard flag.
Return JSON with:
{
  "actions": [
    { "type": string, "target": string, "message": string }
  ]
}
```

## 7. Full analysis prompt example

```
You are an AI risk analyst. Evaluate the following normalized portfolio and produce a complete alert package in JSON.

Portfolio:
{{normalized_portfolio}}

Limits:
- issuer: 8.0%
- sector: 25.0%
- geography: 70.0%
- correlation cluster: correlation > 0.85 for 30-day window

Return only JSON with these fields:
- portfolio_id
- severity
- confidence
- rationale
- exposures
- actions
- audit_notes
```

## 8. Prompt engineering notes
- Always ask Claude to return JSON only.
- Include exact field names and expected data types.
- Use example breach formats when possible.
- Keep prompts concise but specific about the risk domain.
