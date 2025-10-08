# RAG STEP 124 — Update expert metrics (RAG.metrics.update.expert.metrics)

**Type:** process  
**Category:** metrics  
**Node ID:** `UpdateExpertMetrics`

## Intent (Blueprint)
Process orchestrator that updates expert performance metrics based on feedback data. Receives input from Step 123 (CreateFeedbackRec) with expert feedback metadata, coordinates metrics updates using ExpertValidationWorkflow service, and routes to Step 125 (CacheFeedback). Implements thin orchestration pattern with no business logic, focusing on service coordination and context preservation per Mermaid diagram.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/metrics.py:614` - `step_124__update_expert_metrics()`
- **Helper function:** `app/orchestrators/metrics.py:666` - `_update_expert_performance_metrics()`
- **Error handling:** `app/orchestrators/metrics.py:876` - `_handle_metrics_update_error()`
- **Quality calculation:** `app/orchestrators/metrics.py:833` - `_calculate_correction_quality()`
- **Service integration:** `app/services/expert_validation_workflow.py` - `ExpertValidationWorkflow` service
- **Test suite:** `tests/test_rag_step_124_update_expert_metrics.py` (30 comprehensive tests)
- **Status:** 🔌
- **Behavior notes:**
  - Updates expert performance metrics with trust score and accuracy calculations
  - Routes to Step 125 (CacheFeedback) per Mermaid diagram
  - Handles different feedback types with appropriate quality weighting
  - Processes Italian feedback categories with specialized quality impact scoring
  - Validates context data from Step 123 and handles missing/malformed data
  - Preserves all context data while adding metrics update metadata
  - Implements comprehensive error handling with graceful fallback processing
  - Delegates business logic to ExpertValidationWorkflow service following thin orchestration

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async process orchestrator following thin orchestration pattern
- ✅ Added comprehensive expert metrics update coordination and quality calculation
- ✅ Added feedback type-based correction quality calculation (correct: 1.0, incorrect: 0.3, incomplete: 0.7)
- ✅ Added Italian feedback category quality impact scoring with specialized weighting
- ✅ Added context validation from Step 123 with expert metrics data verification
- ✅ Added expert metrics update coordination using ExpertValidationWorkflow service
- ✅ Added routing preparation for Step 125 (CacheFeedback) with feedback caching data
- ✅ Added performance tracking with metrics update timing
- ✅ Added comprehensive observability with structured logging
- ✅ Added comprehensive error handling with graceful fallback and context preservation

## Risks / Impact
- **Low Risk:** Well-tested metrics update logic with comprehensive test coverage (30 tests)
- **Performance:** Minimal latency impact - metrics calculations and database updates are fast
- **Error Handling:** Graceful error handling with fallback processing and context preservation
- **Backwards Compatibility:** Preserves all existing context data while adding metrics metadata
- **Integration:** Works seamlessly with Step 123 input and Step 125 routing per Mermaid flow

## TDD Task List
- [x] Unit tests: 15 comprehensive test cases covering metrics updates, quality calculations, error scenarios
- [x] Integration tests: 10 integration tests covering Step 123→124, 124→125, and full pipeline flows
- [x] Parity tests: 5 behavioral definition tests covering Mermaid compliance and thin orchestration
- [x] Implementation changes:
  - [x] Converted stub to async process orchestrator
  - [x] Added `_update_expert_performance_metrics()` helper function with service coordination
  - [x] Added `_handle_metrics_update_error()` for comprehensive error handling
  - [x] Added `_calculate_correction_quality()` for feedback type-based quality scoring
  - [x] Added `_calculate_category_quality_impact()` for Italian category impact scoring
  - [x] Added expert metrics update coordination using ExpertValidationWorkflow service
  - [x] Added feedback type processing with appropriate quality weighting
  - [x] Added context validation from Step 123 with missing data handling
  - [x] Added routing preparation for Step 125 with feedback caching metadata
  - [x] Added comprehensive error handling with multiple error types
  - [x] Added performance tracking and metrics update timing
  - [x] Added context preservation and pipeline flow continuity
- [x] Observability: added structured log lines
  `RAG STEP 124 (RAG.metrics.update.expert.metrics): Update expert metrics | attrs={...}`
- [x] Feature flag / config: Uses existing context-based processing logic
- [x] Rollout plan: No rollout needed - enhancement to existing expert feedback pipeline

## Done When
- [x] Tests pass (30/30 tests passing);
- [x] metrics/latency acceptable (minimal metrics update time);
- [x] feature behind flag if risky (metrics update with graceful error handling).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->