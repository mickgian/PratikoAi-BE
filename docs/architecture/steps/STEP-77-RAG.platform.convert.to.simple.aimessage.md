# RAG STEP 77 — Convert to simple AIMessage (RAG.platform.convert.to.simple.aimessage)

**Type:** process  
**Category:** platform  
**Node ID:** `SimpleAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SimpleAIMsg` (Convert to simple AIMessage).

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
  `RAG STEP 77 (RAG.platform.convert.to.simple.aimessage): Convert to simple AIMessage | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.27)
   Evidence: Score 0.27, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) evals/helpers.py:21 — evals.helpers.format_messages (score 0.24)
   Evidence: Score 0.24, Format a list of messages for evaluation.

Args:
    messages: List of message d...
3) failure-recovery-system/cicd_integration.py:118 — failure-recovery-system.cicd_integration.CICDEvent.__post_init__ (score 0.24)
   Evidence: Score 0.24, method: __post_init__
4) failure-recovery-system/cicd_integration.py:158 — failure-recovery-system.cicd_integration.RecoveryResponse.__post_init__ (score 0.24)
   Evidence: Score 0.24, method: __post_init__
5) failure-recovery-system/cicd_integration.py:170 — failure-recovery-system.cicd_integration.WebhookSecurityValidator.__init__ (score 0.24)
   Evidence: Score 0.24, method: __init__

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for SimpleAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->