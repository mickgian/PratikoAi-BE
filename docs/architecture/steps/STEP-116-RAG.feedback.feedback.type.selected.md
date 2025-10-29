# RAG STEP 116 — Feedback type selected (RAG.feedback.feedback.type.selected)

**Type:** process  
**Category:** feedback  
**Node ID:** `FeedbackTypeSel`

## Intent (Blueprint)
Process orchestrator that routes feedback to appropriate processing endpoints based on feedback type and context. Takes input from Step 114 (when user provides feedback) and routes to Step 117 (FAQ feedback), Step 118 (KB feedback), or Step 119 (Expert feedback collector) based on priority-based logic. Implements thin orchestration pattern with no business logic, focusing on routing decisions and context preservation.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/feedback.py:466` - `step_116__feedback_type_sel()`
- **Helper function:** `app/orchestrators/feedback.py:445` - `_determine_feedback_routing()`
- **Test suite:** `tests/test_rag_step_116_feedback_type_sel.py` (17 comprehensive tests)
- **Status:** 🔌
- **Behavior notes:**
  - Routes feedback to Step 117 (FAQ), Step 118 (KB), or Step 119 (Expert) based on priority logic
  - Expert user/feedback gets highest priority routing to Step 119
  - Explicit feedback type routing to appropriate endpoints (FAQ→117, KB→118)
  - Contextual detection for implicit feedback type classification
  - Fallback routing to expert feedback collector (Step 119) for unmatched cases
  - Preserves all context data while adding routing metadata

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async process orchestrator following thin orchestration pattern
- ✅ Added priority-based routing logic (expert > explicit > contextual > fallback)
- ✅ Added comprehensive context preservation and routing metadata
- ✅ Added error handling with graceful fallback to expert feedback collector
- ✅ Added performance tracking with routing decision timing
- ✅ Added comprehensive observability with structured logging

## Risks / Impact
- **Low Risk:** Well-tested routing logic with comprehensive test coverage (17 tests)
- **Performance:** Minimal latency impact - routing decisions are fast priority checks
- **Error Handling:** Graceful fallback to expert feedback collector on any routing failures
- **Backwards Compatibility:** Preserves all existing context data while adding routing metadata

## TDD Task List
- [x] Unit tests: 11 comprehensive test cases covering all routing scenarios and edge cases
- [x] Integration tests: 5 integration tests covering Step 114→116, 116→117, 116→119, and full pipeline
- [x] Implementation changes:
  - [x] Converted sync stub to async process orchestrator
  - [x] Added `_determine_feedback_routing()` helper function with priority-based logic
  - [x] Added expert user/feedback priority handling (highest priority)
  - [x] Added explicit feedback type routing (FAQ→117, KB→118)
  - [x] Added contextual feedback detection for implicit classification
  - [x] Added fallback routing to expert feedback collector (Step 119)
  - [x] Added comprehensive context preservation and error handling
- [x] Observability: added structured log lines
  `RAG STEP 116 (RAG.feedback.feedback.type.selected): Feedback type selected | attrs={...}`
- [x] Feature flag / config: Uses existing context-based routing logic
- [x] Rollout plan: No rollout needed - routing enhancement to existing feedback pipeline

## Done When
- [x] Tests pass (17/17 tests passing);
- [x] metrics/latency acceptable (minimal routing decision time);
- [x] feature behind flag if risky (routing logic with graceful fallback).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->