# RAG STEP 2 — User submits query via POST /api/v1/chat (RAG.platform.user.submits.query.via.post.api.v1.chat)

**Type:** startEnd  
**Category:** platform  
**Node ID:** `Start`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Start` (User submits query via POST /api/v1/chat).

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
  `RAG STEP 2 (RAG.platform.user.submits.query.via.post.api.v1.chat): User submits query via POST /api/v1/chat | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/models/user.py:20 — app.models.user.User (score 0.32)
   Evidence: Score 0.32, User model for storing user accounts.

Attributes:
    id: The primary key
    e...
2) app/api/v1/ccnl_calculations.py:31 — app.api.v1.ccnl_calculations.CompensationRequest (score 0.31)
   Evidence: Score 0.31, Request model for compensation calculation.
3) app/api/v1/ccnl_calculations.py:44 — app.api.v1.ccnl_calculations.LeaveBalanceRequest (score 0.31)
   Evidence: Score 0.31, Request model for leave balance calculation.
4) app/api/v1/ccnl_calculations.py:52 — app.api.v1.ccnl_calculations.SeniorityBenefitsRequest (score 0.31)
   Evidence: Score 0.31, Request model for seniority benefits calculation.
5) app/api/v1/ccnl_calculations.py:60 — app.api.v1.ccnl_calculations.ComplexQueryRequest (score 0.31)
   Evidence: Score 0.31, Request model for complex CCNL queries.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->