# RAG STEP 107 — SinglePassStream Prevent double iteration (RAG.preflight.singlepassstream.prevent.double.iteration)

**Type:** process  
**Category:** preflight  
**Node ID:** `SinglePass`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SinglePass` (SinglePassStream Prevent double iteration).

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
  `RAG STEP 107 (RAG.preflight.singlepassstream.prevent.double.iteration): SinglePassStream Prevent double iteration | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/core/streaming_guard.py:19 — app.core.streaming_guard.SinglePassStream.__init__ (score 0.31)
   Evidence: Score 0.31, method: __init__
2) app/core/streaming_guard.py:23 — app.core.streaming_guard.SinglePassStream.__aiter__ (score 0.31)
   Evidence: Score 0.31, method: __aiter__
3) app/core/streaming_guard.py:13 — app.core.streaming_guard.SinglePassStream (score 0.28)
   Evidence: Score 0.28, Wraps an async generator to ensure it's only iterated once.
Raises RuntimeError ...
4) app/services/validators/financial_validation_engine.py:302 — app.services.validators.financial_validation_engine.FinancialValidationEngine.execute_single_task (score 0.25)
   Evidence: Score 0.25, Execute a single validation task.

Args:
    task: The validation task to execut...
5) app/schemas/chat.py:107 — app.schemas.chat.StreamResponse (score 0.23)
   Evidence: Score 0.23, Response model for streaming chat endpoint.

Attributes:
    content: The conten...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->