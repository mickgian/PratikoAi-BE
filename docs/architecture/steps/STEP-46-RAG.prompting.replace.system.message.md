# RAG STEP 46 — Replace system message (RAG.prompting.replace.system.message)

**Type:** process  
**Category:** prompting  
**Node ID:** `ReplaceMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReplaceMsg` (Replace system message).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/prompting.py:669` - `step_46__replace_msg()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator function replaces existing system message with domain-specific prompt when classification is available

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (`tests/test_rag_step_46_replace_system_message.py`)
- [x] Integration tests (parity tests proving identical behavior)
- [x] Implementation changes (orchestrator function implemented and wired)
- [x] Observability: add structured log line
  `RAG STEP 46 (RAG.prompting.replace.system.message): Replace system message | attrs={...}`
- [x] Feature flag / config if needed (none required)
- [x] Rollout plan (direct deployment - no breaking changes)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/prompting.py:669 — app.orchestrators.prompting.step_46__replace_msg (score 0.30)
   Evidence: Score 0.30, RAG STEP 46 — Replace system message
ID: RAG.prompting.replace.system.message
Ty...
2) deployment-orchestration/notification_system.py:764 — deployment-orchestration.notification_system.NotificationManager._create_notification_message (score 0.29)
   Evidence: Score 0.29, Create a formatted notification message.
3) failure-recovery-system/recovery_orchestrator.py:865 — failure-recovery-system.recovery_orchestrator.RecoveryOrchestrator._add_status_message (score 0.29)
   Evidence: Score 0.29, Add a status message to the execution log.
4) deployment-orchestration/notification_system.py:785 — deployment-orchestration.notification_system.NotificationManager._generate_message_content (score 0.28)
   Evidence: Score 0.28, Generate title and body for notification.
5) deployment-orchestration/notification_system.py:109 — deployment-orchestration.notification_system.NotificationMessage (score 0.28)
   Evidence: Score 0.28, A formatted notification message.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ReplaceMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->