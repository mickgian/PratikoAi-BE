# RAG STEP 46 — Replace system message (RAG.prompting.replace.system.message)

**Type:** process  
**Category:** prompting  
**Node ID:** `ReplaceMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ReplaceMsg` (Replace system message).

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
  `RAG STEP 46 (RAG.prompting.replace.system.message): Replace system message | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.29

Top candidates:
1) deployment-orchestration/notification_system.py:764 — deployment-orchestration.notification_system.NotificationManager._create_notification_message (score 0.29)
   Evidence: Score 0.29, Create a formatted notification message.
2) failure-recovery-system/recovery_orchestrator.py:865 — failure-recovery-system.recovery_orchestrator.RecoveryOrchestrator._add_status_message (score 0.29)
   Evidence: Score 0.29, Add a status message to the execution log.
3) app/ragsteps/prompting/step_45_rag_prompting_system_message_exists.py:35 — app.ragsteps.prompting.step_45_rag_prompting_system_message_exists.step_45_rag_prompting_system_message_exists (score 0.28)
   Evidence: Score 0.28, function: step_45_rag_prompting_system_message_exists
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