# RAG STEP 114 — User provides feedback? (RAG.feedback.user.provides.feedback)

**Type:** decision  
**Category:** feedback  
**Node ID:** `FeedbackProvided`

## Intent (Blueprint)
Decision node that evaluates whether user provided feedback after UI display. Routes to appropriate next step based on feedback presence: Step 115 (No feedback) for users who don't provide feedback, or Step 116 (Feedback type selected) for users who provide feedback. Handles multiple feedback formats including user_feedback, expert_feedback, and feedback_data.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/feedback.py:270` - `step_114__feedback_provided()`
- **Helper function:** `app/orchestrators/feedback.py:188` - `_evaluate_feedback_presence()`
- **Test suite:** `tests/test_rag_step_114_feedback_provided.py` (15 comprehensive tests)
- **Status:** 🔌
- **Behavior notes:**
  - Evaluates feedback presence using priority-based detection logic
  - Handles expert feedback (highest priority), user feedback, and general feedback data
  - Routes to Step 115 (No feedback) or Step 116 (Feedback type selected)
  - Preserves all context data while adding decision results
  - Includes comprehensive error handling and performance tracking

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async decision orchestrator following thin orchestration pattern
- ✅ Added comprehensive feedback format detection (user_feedback, expert_feedback, feedback_data)
- ✅ Added priority-based evaluation logic with expert feedback taking precedence
- ✅ Added decision timing and performance tracking
- ✅ Added comprehensive observability with structured logging
- ✅ Added error handling with graceful decision evaluation failures

## Risks / Impact
- **Low Risk:** Well-tested decision logic with comprehensive test coverage
- **Performance:** Minimal latency impact - decision evaluation is fast
- **Error Handling:** Graceful degradation on evaluation failures, defaults to no feedback path
- **Backwards Compatibility:** Preserves all existing context data

## TDD Task List
- [x] Unit tests: 9 comprehensive test cases covering all decision scenarios and feedback formats
- [x] Integration tests: 4 integration tests covering Step 113→114→115/116 flows and full pipeline
- [x] Implementation changes:
  - [x] Converted sync stub to async decision orchestrator
  - [x] Added `_evaluate_feedback_presence()` helper function with priority logic
  - [x] Added feedback format detection (user_feedback, expert_feedback, feedback_data)
  - [x] Added routing decision logic (Step 115 vs Step 116)
  - [x] Added performance tracking and error handling
- [x] Observability: added structured log lines
  `RAG STEP 114 (RAG.feedback.user.provides.feedback): User provides feedback? | attrs={...}`
- [x] Feature flag / config: Uses existing context flags for feedback routing
- [x] Rollout plan: No rollout needed - decision logic enhancement to existing pipeline

## Done When
- [x] Tests pass (15/15 tests passing);
- [x] metrics/latency acceptable (minimal decision evaluation time);
- [x] feature behind flag if risky (uses existing context-based routing).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->