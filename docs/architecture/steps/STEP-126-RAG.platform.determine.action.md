# RAG STEP 126 — Determine action (RAG.platform.determine.action)

**Type:** process  
**Category:** platform  
**Node ID:** `DetermineAction`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DetermineAction` (Determine action).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:3246` - `step_126__determine_action()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator determining next action based on feedback type and validation results. Routes to appropriate feedback handling path.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 126 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/orchestrators/platform.py:3571 — app.orchestrators.platform._determine_feedback_action (score 0.32)
   Evidence: Score 0.32, Determine action to take based on expert feedback analysis.

Applies business lo...
2) app/orchestrators/platform.py:3246 — app.orchestrators.platform.step_126__determine_action (score 0.31)
   Evidence: Score 0.31, RAG STEP 126 — Determine action

ID: RAG.platform.determine.action
Type: process...
3) app/orchestrators/feedback.py:468 — app.orchestrators.feedback._determine_feedback_routing (score 0.27)
   Evidence: Score 0.27, Helper function to determine feedback routing based on context.

Routes feedback...
4) app/orchestrators/streaming.py:80 — app.orchestrators.streaming._determine_streaming_preference (score 0.27)
   Evidence: Score 0.27, Determine if streaming is requested based on various sources.

Priority order:
1...
5) app/models/cassazione.py:311 — app.models.cassazione.determine_related_sectors (score 0.27)
   Evidence: Score 0.27, Determine which CCNL sectors are related to a legal decision.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->