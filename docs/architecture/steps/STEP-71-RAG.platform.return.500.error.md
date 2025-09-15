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
Status: ❌  |  Confidence: 0.12

Top candidates:
1) app/services/ccnl_service.py:153 — app.services.ccnl_service.CCNLValidationResult.add_error (score 0.12)
   Evidence: Score 0.12, Add validation error.
2) app/services/llm_retry_service.py:118 — app.services.llm_retry_service.RetryError (score 0.11)
   Evidence: Score 0.11, Base exception for retry-related errors.
3) evals/main.py:64 — evals.main.print_error (score 0.11)
   Evidence: Score 0.11, Print an error message with colors.

Args:
    message: The message to print
4) version-management/cli/version_cli.py:69 — version-management.cli.version_cli.VersionCLI.print_error (score 0.11)
   Evidence: Score 0.11, Print error message.
5) feature-flags/admin/web_interface.py:1 — feature-flags.admin.web_interface (score 0.11)
   Evidence: Score 0.11, PratikoAI Feature Flag Admin Web Interface

Advanced web-based admin interface f...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for Error500
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->