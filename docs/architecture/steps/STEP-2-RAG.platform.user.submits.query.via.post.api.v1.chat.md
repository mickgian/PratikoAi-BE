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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/api/v1/performance.py:25 — app.api.v1.performance.OptimizeQueryRequest (score 0.27)
   Evidence: Score 0.27, Request to optimize a database query.
2) app/models/encrypted_user.py:278 — app.models.encrypted_user.EncryptedQueryLog (score 0.27)
   Evidence: Score 0.27, Query log model with encrypted query content for privacy compliance.
3) app/schemas/chat.py:57 — app.schemas.chat.QueryClassificationMetadata (score 0.27)
   Evidence: Score 0.27, Metadata about query classification for debugging and monitoring.
4) app/api/v1/ccnl_calculations.py:60 — app.api.v1.ccnl_calculations.ComplexQueryRequest (score 0.27)
   Evidence: Score 0.27, Request model for complex CCNL queries.
5) app/api/v1/gdpr_cleanup.py:64 — app.api.v1.gdpr_cleanup.UserDeletionResponse (score 0.27)
   Evidence: Score 0.27, User data deletion response

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create startEnd implementation for Start
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->