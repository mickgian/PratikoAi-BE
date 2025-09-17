# RAG STEP 47 — Insert system message (RAG.prompting.insert.system.message)

**Type:** process  
**Category:** prompting  
**Node ID:** `InsertMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `InsertMsg` (Insert system message).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 47 (RAG.prompting.insert.system.message): Insert system message | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/ragsteps/prompting/step_47_rag_prompting_insert_system_message.py:61 — app.ragsteps.prompting.step_47_rag_prompting_insert_system_message.insert_system_message (score 0.32)
   Evidence: Score 0.32, Insert system message at the beginning of messages list.

This function provides...
2) app/ragsteps/prompting/step_47_rag_prompting_insert_system_message.py:35 — app.ragsteps.prompting.step_47_rag_prompting_insert_system_message.run (score 0.31)
   Evidence: Score 0.31, Adapter for RAG STEP 47: Insert system message

This step is triggered when:
1. ...
3) deployment-orchestration/notification_system.py:764 — deployment-orchestration.notification_system.NotificationManager._create_notification_message (score 0.29)
   Evidence: Score 0.29, Create a formatted notification message.
4) failure-recovery-system/recovery_orchestrator.py:865 — failure-recovery-system.recovery_orchestrator.RecoveryOrchestrator._add_status_message (score 0.29)
   Evidence: Score 0.29, Add a status message to the execution log.
5) app/ragsteps/prompting/step_45_rag_prompting_system_message_exists.py:35 — app.ragsteps.prompting.step_45_rag_prompting_system_message_exists.step_45_rag_prompting_system_message_exists (score 0.28)
   Evidence: Score 0.28, function: step_45_rag_prompting_system_message_exists

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->