# RAG STEP 106 — Create async generator (RAG.platform.create.async.generator)

**Type:** process  
**Category:** platform  
**Node ID:** `AsyncGen`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AsyncGen` (Create async generator).

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
  `RAG STEP 106 (RAG.platform.create.async.generator): Create async generator | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/orchestrators/platform.py:2384 — app.orchestrators.platform.step_106__async_gen (score 0.29)
   Evidence: Score 0.29, RAG STEP 106 — Create async generator
ID: RAG.platform.create.async.generator
Ty...
2) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.27)
   Evidence: Score 0.27, Create a new FAQ entry.

Requires admin privileges.
3) app/api/v1/auth.py:265 — app.api.v1.auth.create_session (score 0.26)
   Evidence: Score 0.26, Create a new chat session for the authenticated user.

Args:
    user: The authe...
4) app/api/v1/payments.py:35 — app.api.v1.payments.create_customer (score 0.26)
   Evidence: Score 0.26, Create a Stripe customer for the user.

Args:
    request: FastAPI request objec...
5) app/models/ccnl_data.py:813 — app.models.ccnl_data.create_ccnl_id (score 0.26)
   Evidence: Score 0.26, Create standardized CCNL ID.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AsyncGen
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->