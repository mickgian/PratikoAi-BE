# RAG STEP 114 — User provides feedback? (RAG.feedback.user.provides.feedback)

**Type:** decision  
**Category:** feedback  
**Node ID:** `FeedbackProvided`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FeedbackProvided` (User provides feedback?).

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
  `RAG STEP 114 (RAG.feedback.user.provides.feedback): User provides feedback? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.38

Top candidates:
1) app/models/user.py:60 — app.models.user.User.set_refresh_token_hash (score 0.38)
   Evidence: Score 0.38, Set the hash of the refresh token.

Stores a bcrypt hash of the refresh token fo...
2) app/services/expert_feedback_collector.py:1 — app.services.expert_feedback_collector (score 0.37)
   Evidence: Score 0.37, Expert Feedback Collection Service for Quality Analysis System.

Handles collect...
3) app/models/quality_analysis.py:27 — app.models.quality_analysis.FeedbackType (score 0.34)
   Evidence: Score 0.34, Types of expert feedback
4) app/models/quality_analysis.py:361 — app.models.quality_analysis.ExpertValidation (score 0.33)
   Evidence: Score 0.33, Expert validation records for complex queries
5) app/services/validators/financial_validation_engine.py:187 — app.services.validators.financial_validation_engine.FinancialValidationEngine.__init__ (score 0.33)
   Evidence: Score 0.33, Initialize the Financial Validation Engine.

Args:
    config: Engine configurat...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->