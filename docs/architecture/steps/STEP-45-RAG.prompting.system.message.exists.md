# RAG STEP 45 — System message exists? (RAG.prompting.system.message.exists)

**Type:** decision  
**Category:** prompting  
**Node ID:** `CheckSysMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheckSysMsg` (System message exists?).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** missing
- **Paths / classes:** `app/orchestrators/prompting.py:568` - `step_45__check_sys_msg()`
- **Behavior notes:** Runtime boundary; checks if system message exists; routes to replacement or insertion steps.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 45 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/prompting.py:568 — app.orchestrators.prompting.step_45__check_sys_msg (score 0.31)
   Evidence: Score 0.31, RAG STEP 45 — System message exists?
ID: RAG.prompting.system.message.exists
Typ...
2) app/orchestrators/platform.py:971 — app.orchestrators.platform.step_13__message_exists (score 0.28)
   Evidence: Score 0.28, RAG STEP 13 — User message exists?
ID: RAG.platform.user.message.exists
Type: de...
3) validate_italian_implementation.py:8 — validate_italian_implementation.check_file_exists (score 0.28)
   Evidence: Score 0.28, Check if a file exists and return status.
4) validate_payment_implementation.py:8 — validate_payment_implementation.check_file_exists (score 0.28)
   Evidence: Score 0.28, Check if a file exists and return status.
5) deployment-orchestration/notification_system.py:764 — deployment-orchestration.notification_system.NotificationManager._create_notification_message (score 0.28)
   Evidence: Score 0.28, Create a formatted notification message.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Node step requires LangGraph wiring to be considered fully implemented

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->