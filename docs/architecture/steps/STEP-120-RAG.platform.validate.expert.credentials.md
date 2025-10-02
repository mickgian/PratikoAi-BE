# RAG STEP 120 — Validate expert credentials (RAG.platform.validate.expert.credentials)

**Type:** process  
**Category:** platform  
**Node ID:** `ValidateExpert`

## Intent (Blueprint)
Process orchestrator that validates expert credentials and calculates trust scores for expert feedback routing. Receives input from Step 119 (ExpertFeedbackCollector), validates expert credentials and professional qualifications, calculates trust scores based on credentials/experience/track record, and routes to Step 121 (TrustScoreOK decision). Implements thin orchestration pattern with no business logic, focusing on credential validation coordination and trust score preparation.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:2705` - `step_120__validate_expert()`
- **Helper function:** `app/orchestrators/platform.py:2610` - `_validate_expert_credentials()`
- **Trust scoring:** `app/orchestrators/platform.py:2656` - `_calculate_trust_score()`
- **Test suite:** `tests/test_rag_step_120_validate_expert.py` (15 comprehensive tests)
- **Status:** ✅ Implemented (async process orchestrator with expert credential validation)
- **Behavior notes:**
  - Validates expert credentials with comprehensive trust scoring algorithm
  - Routes to Step 121 (TrustScoreOK decision) per Mermaid diagram
  - Handles Italian tax professional certification recognition with bonus scoring
  - Calculates weighted trust scores: credentials (50%), experience (30%), track record (30%)
  - Validates expert profiles with required fields and professional qualifications
  - Preserves all context data while adding validation metadata and trust scores
  - Handles errors gracefully with fallback routing to trust score decision

## Differences (Blueprint vs Current)
- ✅ Fully implemented as async process orchestrator following thin orchestration pattern
- ✅ Added comprehensive expert credential validation and trust scoring logic
- ✅ Added Italian tax professional certification recognition with specialized scoring
- ✅ Added weighted trust score calculation based on credentials, experience, track record
- ✅ Added professional qualification validation for regulatory compliance
- ✅ Added error handling with graceful fallback to trust score decision routing
- ✅ Added performance tracking with credential validation timing
- ✅ Added comprehensive observability with structured logging
- ✅ Integrated with existing context preservation patterns from other RAG steps

## Risks / Impact
- **Low Risk:** Well-tested credential validation logic with comprehensive test coverage (15 tests)
- **Performance:** Minimal latency impact - validation operations are fast and cached
- **Error Handling:** Graceful error handling with fallback routing to trust score decision
- **Backwards Compatibility:** Preserves all existing context data while adding validation metadata
- **Integration:** Works seamlessly with Step 119 input and Step 121 routing per Mermaid flow

## TDD Task List
- [x] Unit tests: 10 comprehensive test cases covering validation, trust scoring, and error scenarios
- [x] Integration tests: 5 integration tests covering Step 119→120, 120→121, and full pipeline flows
- [x] Implementation changes:
  - [x] Converted sync stub to async process orchestrator
  - [x] Added `_validate_expert_credentials()` helper function with validation logic
  - [x] Added `_calculate_trust_score()` helper function with weighted scoring algorithm
  - [x] Added expert credential validation and professional qualification checks
  - [x] Added Italian tax professional certification recognition and bonus scoring
  - [x] Added trust score calculation with credentials/experience/track record weighting
  - [x] Added comprehensive error handling with multiple error types and fallback routing
  - [x] Added performance tracking and validation timing
  - [x] Added context preservation and routing to Step 121 (TrustScoreOK decision)
- [x] Observability: added structured log lines
  `RAG STEP 120 (RAG.platform.validate.expert.credentials): Validate expert credentials | attrs={...}`
- [x] Feature flag / config: Uses existing context-based processing logic
- [x] Rollout plan: No rollout needed - enhancement to existing expert validation pipeline

## Done When
- [x] Tests pass (15/15 tests passing);
- [x] metrics/latency acceptable (minimal validation time);
- [x] feature behind flag if risky (credential validation with graceful error handling).

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.37

Top candidates:
1) app/orchestrators/platform.py:3041 — app.orchestrators.platform._validate_expert_credentials (score 0.37)
   Evidence: Score 0.37, Helper function to validate expert credentials and calculate trust score.

Handl...
2) app/orchestrators/platform.py:3172 — app.orchestrators.platform.step_120__validate_expert (score 0.30)
   Evidence: Score 0.30, RAG STEP 120 — Validate expert credentials.

Process orchestrator that validates...
3) app/services/expert_feedback_collector.py:149 — app.services.expert_feedback_collector.ExpertFeedbackCollector._validate_feedback_data (score 0.30)
   Evidence: Score 0.30, Validate feedback data structure and content
4) app/services/expert_validation_workflow.py:371 — app.services.expert_validation_workflow.ExpertValidationWorkflow._calculate_credentials_score (score 0.29)
   Evidence: Score 0.29, Calculate score based on professional credentials
5) app/services/expert_validation_workflow.py:430 — app.services.expert_validation_workflow.ExpertValidationWorkflow._validate_regulatory_references (score 0.29)
   Evidence: Score 0.29, Validate regulatory references for accuracy and currency

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->