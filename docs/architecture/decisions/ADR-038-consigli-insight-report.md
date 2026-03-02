# ADR-038: /consigli — On-Demand AI Insight Report

## Status
APPROVED WITH CONDITIONS — @egidio review 2026-03-01 (8/10 compliance, GDPR PASS)

## Date
2026-03-01

## Context

PratikoAI's 134-step RAG pipeline captures rich interaction data per user:
chat history, query types, domain classifications, KB sources used, response
quality signals, failure patterns, and usage metrics. Today this data powers
internal dashboards (cost monitoring, quality metrics, proactivity analytics)
but **none of it is surfaced back to the user as actionable insight**.

### Business Need
Users (Italian tax/labor consultants) need to understand how they use PratikoAI
so they can:
1. Discover features they underutilize
2. Identify knowledge domains they frequently query (and where answers are weak)
3. Improve their query formulation for better results
4. Understand their interaction patterns and optimize workflow

### Design Constraints (from stakeholder input)
- **NO cost accountability** — Users must NOT see LLM costs, token usage, or
  per-query pricing. The billing system (ADR-027) handles cost exposure via
  rolling windows and plan limits; the insight report is purely behavioral.
- **On-demand only** — No automatic scheduled reports. Triggered by `/consigli`
  slash command.
- **Data sufficiency gate** — Report generation refused when insufficient data
  exists (minimum threshold required for meaningful analysis).
- **Per-user scoping** — Insights are strictly per-user, never cross-user or
  cross-studio aggregation exposed to users.
- **Production LLM model** — Use the same model as production chat
  (`mistral:mistral-large-latest` via `PRODUCTION_LLM_MODEL`).
- **HTML output** — Produces a self-contained HTML report (analogous to Claude
  Code `/insights`), returned as downloadable artifact.
- **GDPR compliance** — Must respect consent, anonymization, and retention
  policies (ADR-037).

## Decision

Implement a `/consigli` slash command that generates an on-demand HTML insight
report analyzing the user's interaction history across 5 facet dimensions.

### Architecture Overview

```
User types "/consigli"
    │
    ▼
SlashCommandHandler.parse() → {"command": "consigli"}
    │
    ▼
ConsigliService.can_generate(user_id, db)
    │ Check minimum data thresholds
    │ (≥20 queries, ≥7 days of history)
    ├── Insufficient → Return Italian message explaining why
    │
    ▼
ConsigliService.generate_report(user_id, db)
    │
    ├── 1. Collect raw data (ChatHistoryService, UsageTracker)
    │      - Query history (text, types, timestamps, domains)
    │      - Session patterns (frequency, duration, time-of-day)
    │      - KB source usage (which knowledge bases hit)
    │      - Quality signals (cache hits, response times)
    │      - Proactivity engagement (action clicks, question answers)
    │
    ├── 2. Compute statistical facets (pure Python, no LLM)
    │      - Temporal patterns (peak hours, weekday vs weekend)
    │      - Domain distribution (tax, labor, legal, etc.)
    │      - Query complexity trends
    │      - Feature usage rates
    │
    ├── 3. LLM analysis (mistral-large-latest)
    │      - Synthesize behavioral patterns into natural language
    │      - Generate actionable recommendations in Italian
    │      - Identify knowledge gaps and suggest improvements
    │      - NO cost/pricing/token data in prompt
    │
    ├── 4. Render HTML report (Jinja2 template)
    │      - Self-contained HTML (inline CSS, no external deps)
    │      - Italian language throughout
    │      - 5 facet sections + executive summary
    │
    └── 5. Return report as downloadable artifact
```

### Facet Dimensions

| # | Facet | Data Source | Analysis Type |
|---|-------|-----------|---------------|
| 1 | **Pattern comportamentali** (Behavioral patterns) | Session timestamps, query frequency, time-of-day | Statistical + LLM narrative |
| 2 | **Competenza per dominio** (Domain proficiency) | Query types, domain classifications, KB sources | Statistical + LLM recommendations |
| 3 | **Qualità dell'interazione** (Interaction quality) | Cache hits, follow-up questions, query reformulations | Statistical + LLM tips |
| 4 | **Lacune di conoscenza** (Knowledge gaps) | Failed queries, low-quality responses, repeated topics | Statistical + LLM suggestions |
| 5 | **Ottimizzazione del workflow** (Workflow optimization) | Feature usage, proactivity engagement, session patterns | Statistical + LLM recommendations |

### Data Sufficiency Gate

Before generating a report, the service checks:

```python
MIN_QUERIES = 20        # Minimum queries for meaningful analysis
MIN_HISTORY_DAYS = 7    # Minimum span of interaction history
```

If thresholds are not met, return an Italian message:
> "Non ci sono ancora dati sufficienti per generare un report significativo.
> Continua a utilizzare PratikoAI e riprova tra qualche giorno."

### GDPR Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Consent** | Requires ANALYTICAL consent type (existing ConsentManager) |
| **Data minimization** | Only aggregate/anonymized data sent to LLM |
| **No PII in prompt** | User queries anonymized before LLM analysis |
| **Retention** | Reports not persisted server-side; generated on-the-fly |
| **Right to object** | Can withdraw ANALYTICAL consent to disable feature |
| **Audit logging** | GDPR log entry (step_004 pattern) for report generation |

### Multi-Tenant Isolation (RC-1)

The `query_history` table is scoped by `user_id`, not `studio_id`. Tenant
isolation is enforced indirectly: the authenticated user is bound to exactly
one studio via the session/auth layer (`Session.studio_id`), and `user_id` is
extracted from the authenticated session. This means a user can only access
their own query history, which belongs to their studio. Cross-studio data
access is prevented by the auth layer, not by a direct `studio_id` column on
`query_history`.

### Rate Limiting (RC-2)

Report generation is limited to **3 requests per user per 24 hours** (enforced
via the existing `@limiter` pattern from `app.core.limiter`). Excess requests
return HTTP 429 with an Italian message:
> "Hai già generato il massimo numero di report oggi. Riprova domani."

### Cost Tracking (RC-3)

The LLM call for report generation is tracked via
`usage_tracker.track_llm_usage()` with `api_type="consigli_report"`. This
ensures the cost counts against the user's billing plan limits (ADR-027
rolling windows) and appears in cost monitoring dashboards.

### Concurrency Guard (RC-4)

If a report generation is already in progress for a user, subsequent
`/consigli` commands return an Italian message:
> "Un report è in fase di generazione. Attendere il completamento."

Implementation: Redis key `consigli:generating:{user_id}` with 90-second TTL.

### PII Protection Strategy

The LLM prompt receives **only aggregated statistics and anonymized patterns**,
never raw user queries. Specifically:

1. Query text is NOT sent to the LLM — only query type classifications
   (e.g., "tax_calculation", "labor_question"), domain labels, and counts
2. Temporal data is aggregated (e.g., "most active: Tuesday mornings")
3. KB source names are included (public knowledge base names, not user content)
4. The anonymizer (existing `app/core/privacy/anonymizer.py`) is applied to
   any textual context before LLM prompt assembly
5. LLM system prompt includes: "Non includere mai nomi, email, codici fiscali,
   o altri dati personali nel report"
6. LLM output is run through the anonymizer as a safety net before rendering

### LLM Model Selection

Use `PRODUCTION_LLM_MODEL` (currently `mistral:mistral-large-latest`) via
the existing `ModelRegistry.resolve_production_model()`. Rationale:

- Report generation is a **premium, user-facing feature** — quality matters
- Frequency is low (on-demand, not per-query) — cost impact minimal
- Consistency with production chat model ensures familiar Italian quality
- Timeout: 90 seconds (same as model comparison feature)

### HTML Report Structure

```html
<!-- Self-contained, no external dependencies -->
<html lang="it">
<head>
  <style>/* Inline CSS — PratikoAI brand colors */</style>
</head>
<body>
  <header>PratikoAI — Report Consigli Personalizzati</header>
  <section id="sommario"><!-- Executive summary --></section>
  <section id="pattern-comportamentali"><!-- Facet 1 --></section>
  <section id="competenza-dominio"><!-- Facet 2 --></section>
  <section id="qualita-interazione"><!-- Facet 3 --></section>
  <section id="lacune-conoscenza"><!-- Facet 4 --></section>
  <section id="ottimizzazione-workflow"><!-- Facet 5 --></section>
  <footer>Generato il {date} — Dati degli ultimi 90 giorni</footer>
</body>
</html>
```

### Slash Command Integration

Extends existing `SlashCommandHandler` (DEV-402) pattern:

```python
# New pattern alongside existing /procedura
SLASH_CONSIGLI_RE = re.compile(r"^/consigli$", re.IGNORECASE)
```

No arguments needed — always generates for the authenticated user.

### Feature Activation

- Controlled via Flagsmith feature flag: `consigli_report_enabled`
- Initially disabled in production, enabled per-studio for beta testing
- Uses existing `feature_flag_service.is_enabled()` with studio-level override

## File Structure

```
app/
├── services/
│   └── consigli_service.py        # Core report generation (<200 lines)
├── schemas/
│   └── consigli.py                # Response schemas (<50 lines)
└── templates/
    └── consigli_report.html       # Jinja2 HTML template
```

Changes to existing files:
- `app/services/slash_command_handler.py` — Add `/consigli` pattern + handler
- `app/api/v1/chatbot.py` — Wire slash command dispatch (if not already wired)

## Consequences

### Positive
- Users gain actionable self-improvement insights without cost exposure
- Leverages existing data infrastructure (no new data collection needed)
- On-demand model avoids background processing costs
- GDPR-compliant by design (no PII in LLM prompts, no server-side persistence)
- Follows established slash command pattern (DEV-402)

### Negative
- Single LLM call per report generation (~€0.01-0.03 per report)
- Report quality depends on sufficient interaction history
- HTML template maintenance

### Risks
- **Data sparsity** — Mitigated by sufficiency gate (20 queries, 7 days)
- **LLM hallucination in recommendations** — Mitigated by grounding in
  statistical data computed before LLM call
- **Performance** — Single LLM call, 90s timeout, acceptable for on-demand use

## Alternatives Considered

### 1. Scheduled automatic reports
Rejected: User requested on-demand only. Avoids unnecessary LLM costs and
aligns with ADR-035 (notification-only proactive delivery — no in-chat
suggestions).

### 2. Per-query micro-insights
Rejected: Would add latency to every query. On-demand report is more focused
and cost-efficient.

### 3. Dashboard UI instead of HTML report
Rejected for MVP: HTML report is simpler to implement and can be shared/printed.
Dashboard can be added later as an enhancement.

### 4. BASIC tier model for analysis
Rejected: User explicitly requested production model. Report is low-frequency
so premium model cost is negligible.
