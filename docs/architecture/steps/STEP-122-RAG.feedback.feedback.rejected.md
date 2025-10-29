# RAG STEP 122 — Feedback rejected (RAG.feedback.feedback.rejected)

**Type:** error  
**Category:** feedback  
**Node ID:** `FeedbackRejected`

## Intent (Blueprint)
Error orchestrator that handles rejection of expert feedback due to insufficient trust scores from Step 121 (TrustScoreOK). Receives input when trust score < 0.7, processes feedback rejection with comprehensive logging, and terminates the feedback pipeline. Implements thin orchestration pattern with no business logic, focusing on rejection coordination, outcome tracking, and pipeline termination per Mermaid diagram.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/feedback.py:668` - `step_122__feedback_rejected()`
- **Helper function:** `app/orchestrators/feedback.py:611` - `_process_feedback_rejection()`
- **Test suite:** `tests/test_rag_step_122_feedback_rejected.py` (13 comprehensive tests)
- **Status:** 🔌
- **Behavior notes:**
  - Processes expert feedback rejection with comprehensive metadata generation
  - Handles rejection due to insufficient trust scores (< 0.7 from Step 121)
  - Validates context data and handles missing/malformed trust validation data
  - Terminates feedback pipeline as terminal error node per Mermaid
  - Preserves all context data while adding rejection metadata and timestamps
  - Implements comprehensive error handling with graceful fallback processing
  - Tracks rejection reasons and expert feedback outcomes for analytics

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async error orchestrator following thin orchestration pattern
- ✅ Added comprehensive feedback rejection processing and metadata generation
- ✅ Added trust score validation and rejection reason classification
- ✅ Added context validation with graceful handling of missing/malformed data
- ✅ Added pipeline termination logic as terminal error node per Mermaid
- ✅ Added rejection timestamp tracking and expert feedback outcome logging
- ✅ Added performance tracking with rejection processing timing
- ✅ Added comprehensive observability with structured logging
- ✅ Integrated with existing orchestrator patterns from Step 121 routing

## Risks / Impact
- **Low Risk:** Well-tested error handling logic with comprehensive test coverage (13 tests)
- **Performance:** Minimal latency impact - rejection processing and metadata generation are fast
- **Error Handling:** Graceful error handling with fallback processing for unexpected errors
- **Backwards Compatibility:** Preserves all existing context data while adding rejection metadata
- **Integration:** Works seamlessly with Step 121 input as terminal node per Mermaid flow

## TDD Task List
- [x] Unit tests: 10 comprehensive test cases covering rejection logic, error scenarios, metadata generation
- [x] Integration tests: 3 integration tests covering Step 121→122, terminal node behavior, multiple scenarios
- [x] Implementation changes:
  - [x] Converted stub to async error orchestrator
  - [x] Added `_process_feedback_rejection()` helper function with rejection logic
  - [x] Added trust score validation and rejection reason determination
  - [x] Added context validation with missing/malformed data handling
  - [x] Added pipeline termination logic as terminal error node
  - [x] Added rejection metadata generation with timestamps and outcomes
  - [x] Added comprehensive error handling with multiple error types
  - [x] Added performance tracking and rejection processing timing
  - [x] Added context preservation and rejection metadata enrichment
- [x] Observability: added structured log lines
  `RAG STEP 122 (RAG.feedback.feedback.rejected): Feedback rejected | attrs={...}`
- [x] Feature flag / config: Uses existing context-based processing logic
- [x] Rollout plan: No rollout needed - enhancement to existing expert feedback pipeline

## Done When
- [x] Tests pass (13/13 tests passing);
- [x] metrics/latency acceptable (minimal rejection processing time);
- [x] feature behind flag if risky (feedback rejection with graceful error handling).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->