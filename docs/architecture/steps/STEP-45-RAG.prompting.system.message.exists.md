# RAG STEP 45 — System message exists? (RAG.prompting.system.message.exists)

**Type:** decision  
**Category:** prompting  
**Node ID:** `CheckSysMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CheckSysMsg` (System message exists?).

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
  `RAG STEP 45 (RAG.prompting.system.message.exists): System message exists? | attrs={...}`
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
1) app/core/langgraph/graph.py:31 — app.core.langgraph.graph.step_45_rag_prompting_system_message_exists (score 0.29)
   Evidence: Score 0.29, function: step_45_rag_prompting_system_message_exists
2) validate_italian_implementation.py:8 — validate_italian_implementation.check_file_exists (score 0.28)
   Evidence: Score 0.28, Check if a file exists and return status.
3) validate_payment_implementation.py:8 — validate_payment_implementation.check_file_exists (score 0.28)
   Evidence: Score 0.28, Check if a file exists and return status.
4) deployment-orchestration/notification_system.py:764 — deployment-orchestration.notification_system.NotificationManager._create_notification_message (score 0.28)
   Evidence: Score 0.28, Create a formatted notification message.
5) deployment-orchestration/notification_system.py:924 — deployment-orchestration.notification_system.NotificationManager._check_conditions (score 0.28)
   Evidence: Score 0.28, Check if context matches the rule conditions.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for CheckSysMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->