# RAG STEP 113 — FeedbackUI.show_options Correct Incomplete Wrong (RAG.feedback.feedbackui.show.options.correct.incomplete.wrong)

**Type:** process  
**Category:** feedback  
**Node ID:** `FeedbackUI`

## Intent (Blueprint)
Display feedback UI options (Correct, Incomplete, Wrong) to users after presenting AI responses. This step enables users to provide quality feedback that can be used for response evaluation and model improvement. The step handles different user types (anonymous, registered, expert) with appropriate feedback option sets and supports Italian localization for tax domain feedback.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/feedback.py:129` - `step_113__feedback_ui()`
- **Helper function:** `app/orchestrators/feedback.py:14` - `_display_feedback_ui_options()`
- **Test suite:** `tests/test_rag_step_113_feedback_ui.py` (16 comprehensive tests)
- **Status:** ✅ Implemented (async orchestrator with full functionality)
- **Behavior notes:**
  - Displays feedback options based on user type and configuration
  - Supports Italian localized feedback categories for tax domain
  - Handles expert user enhancements with trust scoring
  - Preserves all context data while adding UI elements
  - Includes comprehensive error handling and graceful degradation

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async orchestrator following thin orchestration pattern
- ✅ Added comprehensive user type handling (anonymous, registered, expert)
- ✅ Added Italian localization support for tax domain feedback
- ✅ Added expert mode enhancements with confidence ratings and improvement suggestions
- ✅ Added comprehensive observability with structured logging
- ✅ Added error handling with graceful UI display failures

## Risks / Impact
- **Low Risk:** Well-tested implementation with comprehensive test coverage
- **Performance:** Minimal latency impact - UI generation is fast
- **Error Handling:** Graceful degradation on failures, never blocks pipeline
- **Backwards Compatibility:** Preserves all existing context data

## TDD Task List
- [x] Unit tests: 10 comprehensive test cases covering all user types, configurations, and error scenarios
- [x] Integration tests: 6 integration tests covering Step 111→113→114 flow and full pipeline
- [x] Implementation changes:
  - [x] Converted sync stub to async orchestrator
  - [x] Added `_display_feedback_ui_options()` helper function
  - [x] Added user type detection and option customization
  - [x] Added Italian localization support
  - [x] Added expert mode enhancements
  - [x] Added comprehensive error handling
- [x] Observability: added structured log lines
  `RAG STEP 113 (RAG.feedback.feedbackui.show.options.correct.incomplete.wrong): FeedbackUI.show_options Correct Incomplete Wrong | attrs={...}`
- [x] Feature flag / config: Uses existing context flags for anonymous/expert feedback
- [x] Rollout plan: No rollout needed - graceful enhancement to existing pipeline

## Done When
- [x] Tests pass (16/16 tests passing);
- [x] metrics/latency acceptable (minimal performance impact);
- [x] feature behind flag if risky (uses existing context flags).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.49

Top candidates:
1) app/services/automatic_improvement_engine.py:1 — app.services.automatic_improvement_engine (score 0.49)
   Evidence: Score 0.49, Automatic Improvement Engine for Quality Analysis System.

Automatically generat...
2) app/services/expert_feedback_collector.py:31 — app.services.expert_feedback_collector.ExpertFeedbackCollector (score 0.48)
   Evidence: Score 0.48, Service for collecting and processing expert feedback on AI responses.

Features...
3) app/orchestrators/feedback.py:783 — app.orchestrators.feedback._create_expert_feedback_record (score 0.45)
   Evidence: Score 0.45, Helper function to create expert feedback record using ExpertFeedbackCollector s...
4) app/services/expert_feedback_collector.py:149 — app.services.expert_feedback_collector.ExpertFeedbackCollector._validate_feedback_data (score 0.45)
   Evidence: Score 0.45, Validate feedback data structure and content
5) app/services/expert_feedback_collector.py:1 — app.services.expert_feedback_collector (score 0.45)
   Evidence: Score 0.45, Expert Feedback Collection Service for Quality Analysis System.

Handles collect...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->