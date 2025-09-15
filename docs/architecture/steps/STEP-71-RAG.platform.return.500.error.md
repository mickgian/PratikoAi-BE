# RAG STEP 71 — Return 500 error (RAG.platform.return.500.error)

**Type:** error  
**Category:** platform  
**Node ID:** `Error500`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Error500` (Return 500 error).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 71 (RAG.platform.return.500.error): Return 500 error | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.20

Top candidates:
1) evals/main.py:64 — evals.main.print_error (score 0.20)
   Evidence: Score 0.20, Print an error message with colors.

Args:
    message: The message to print
2) app/models/query.py:131 — app.models.query.QueryErrorResponse (score 0.19)
   Evidence: Score 0.19, Error response for failed queries.
3) version-management/cli/version_cli.py:69 — version-management.cli.version_cli.VersionCLI.print_error (score 0.19)
   Evidence: Score 0.19, Print error message.
4) app/models/cassazione_data.py:355 — app.models.cassazione_data.ScrapingError (score 0.19)
   Evidence: Score 0.19, Represents a scraping error with context.
5) app/services/automatic_improvement_engine.py:28 — app.services.automatic_improvement_engine.ImprovementEngineError (score 0.19)
   Evidence: Score 0.19, Custom exception for improvement engine operations

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error500
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->