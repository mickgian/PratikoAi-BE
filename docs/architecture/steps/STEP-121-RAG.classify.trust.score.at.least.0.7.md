# RAG STEP 121 — Trust score at least 0.7? (RAG.classify.trust.score.at.least.0.7)

**Type:** decision  
**Category:** classify  
**Node ID:** `TrustScoreOK`

## Intent (Blueprint)
Decision orchestrator that evaluates trust scores from Step 120 (ValidateExpert) against 0.7 threshold and routes to appropriate next steps. Receives trust score validation data, makes binary decision based on 0.7 threshold per Mermaid, and routes to either Step 122 (FeedbackRejected) or Step 123 (CreateFeedbackRec). Implements thin orchestration pattern with no business logic, focusing on decision coordination and routing control flow per Mermaid diagram.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/classify.py:1056` - `step_121__trust_score_ok()`
- **Helper function:** `app/orchestrators/classify.py:985` - `_evaluate_trust_score_decision()`
- **Test suite:** `tests/test_rag_step_121_trust_score_ok.py` (15 comprehensive tests)
- **Status:** ✅ Implemented (async decision orchestrator with trust score evaluation)
- **Behavior notes:**
  - Evaluates trust scores against 0.7 threshold per Mermaid specification
  - Routes to Step 122 (FeedbackRejected) for scores < 0.7
  - Routes to Step 123 (CreateFeedbackRec) for scores >= 0.7
  - Handles invalid/missing trust scores gracefully with rejection fallback
  - Validates trust score ranges (0-1) and handles NaN/infinite values
  - Preserves all context data while adding decision metadata
  - Implements comprehensive error handling with graceful fallback routing

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async decision orchestrator following thin orchestration pattern
- ✅ Added comprehensive trust score evaluation logic with threshold comparison
- ✅ Added trust score validation (range checking, NaN/infinity handling)
- ✅ Added missing/invalid trust score error handling with rejection fallback
- ✅ Added context preservation and decision metadata enrichment
- ✅ Added routing logic per Mermaid: >= 0.7 → CreateFeedbackRec, < 0.7 → FeedbackRejected
- ✅ Added performance tracking with decision timing
- ✅ Added comprehensive observability with structured logging
- ✅ Integrated with existing orchestrator patterns from Steps 120 and beyond

## Risks / Impact
- **Low Risk:** Well-tested decision logic with comprehensive test coverage (15 tests)
- **Performance:** Minimal latency impact - threshold comparison and decision routing are fast
- **Error Handling:** Graceful error handling with fallback routing to rejection
- **Backwards Compatibility:** Preserves all existing context data while adding decision metadata
- **Integration:** Works seamlessly with Step 120 input and Steps 122/123 routing per Mermaid flow

## TDD Task List
- [x] Unit tests: 10 comprehensive test cases covering decision logic, boundary conditions, error scenarios
- [x] Integration tests: 5 integration tests covering Step 120→121, 121→122, 121→123, and full pipeline flows
- [x] Implementation changes:
  - [x] Converted stub to async decision orchestrator
  - [x] Added `_evaluate_trust_score_decision()` helper function with threshold logic
  - [x] Added trust score validation and range checking (0-1, NaN/infinity handling)
  - [x] Added binary decision logic: >= 0.7 threshold per Mermaid specification
  - [x] Added routing coordination to Steps 122 (FeedbackRejected) and 123 (CreateFeedbackRec)
  - [x] Added missing/invalid trust score error handling with rejection fallback
  - [x] Added comprehensive error handling with multiple error types
  - [x] Added performance tracking and decision timing
  - [x] Added context preservation and decision metadata enrichment
- [x] Observability: added structured log lines
  `RAG STEP 121 (RAG.classify.trust.score.at.least.0.7): Trust score at least 0.7? | attrs={...}`
- [x] Feature flag / config: Uses existing context-based processing logic
- [x] Rollout plan: No rollout needed - enhancement to existing expert validation pipeline

## Done When
- [x] Tests pass (15/15 tests passing);
- [x] metrics/latency acceptable (minimal decision evaluation time);
- [x] feature behind flag if risky (trust score decision with graceful error handling).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.47

Top candidates:
1) app/orchestrators/classify.py:210 — app.orchestrators.classify.step_31__classify_domain (score 0.47)
   Evidence: Score 0.47, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
2) app/orchestrators/classify.py:544 — app.orchestrators.classify.step_35__llmfallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
3) app/orchestrators/classify.py:317 — app.orchestrators.classify.step_32__calc_scores (score 0.44)
   Evidence: Score 0.44, RAG STEP 32 — Calculate domain and action scores Match Italian keywords
ID: RAG....
4) app/orchestrators/classify.py:677 — app.orchestrators.classify.step_35__llm_fallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
5) app/orchestrators/classify.py:433 — app.orchestrators.classify.step_33__confidence_check (score 0.40)
   Evidence: Score 0.40, RAG STEP 33 — Confidence at least threshold?
ID: RAG.classify.confidence.at.leas...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->