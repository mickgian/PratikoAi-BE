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
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/models/user.py:20 — app.models.user.User (score 0.26)
   Evidence: Score 0.26, User model for storing user accounts.

    Attributes:
        id: The primary k...
2) app/api/v1/ccnl_calculations.py:31 — app.api.v1.ccnl_calculations.CompensationRequest (score 0.25)
   Evidence: Score 0.25, Request model for compensation calculation.
3) app/api/v1/ccnl_calculations.py:44 — app.api.v1.ccnl_calculations.LeaveBalanceRequest (score 0.25)
   Evidence: Score 0.25, Request model for leave balance calculation.
4) app/api/v1/ccnl_calculations.py:52 — app.api.v1.ccnl_calculations.SeniorityBenefitsRequest (score 0.25)
   Evidence: Score 0.25, Request model for seniority benefits calculation.
5) app/api/v1/ccnl_calculations.py:60 — app.api.v1.ccnl_calculations.ComplexQueryRequest (score 0.25)
   Evidence: Score 0.25, Request model for complex CCNL queries.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create startEnd implementation for Start
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->