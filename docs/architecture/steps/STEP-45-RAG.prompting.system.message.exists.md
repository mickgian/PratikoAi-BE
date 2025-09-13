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
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.32)
   Evidence: Score 0.32, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) failure-recovery-system/cicd_integration.py:1196 — failure-recovery-system.cicd_integration.create_webhook_endpoints (score 0.32)
   Evidence: Score 0.32, Create webhook endpoints for different platforms.
3) rollback-system/health_monitor.py:163 — rollback-system.health_monitor.ApplicationHealthChecker.__init__ (score 0.32)
   Evidence: Score 0.32, method: __init__
4) rollback-system/health_monitor.py:318 — rollback-system.health_monitor.LogPreserver.__init__ (score 0.32)
   Evidence: Score 0.32, method: __init__
5) rollback-system/health_monitor.py:401 — rollback-system.health_monitor.HealthMonitor.__init__ (score 0.32)
   Evidence: Score 0.32, method: __init__

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->