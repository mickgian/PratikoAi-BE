# RAG STEP 98 — Convert to ToolMessage facts and spans (RAG.facts.convert.to.toolmessage.facts.and.spans)

**Type:** process  
**Category:** facts  
**Node ID:** `ToToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToToolResults` (Convert to ToolMessage facts and spans).

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
  `RAG STEP 98 (RAG.facts.convert.to.toolmessage.facts.and.spans): Convert to ToolMessage facts and spans | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.20

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.20)
   Evidence: Score 0.20, Validate the message content.

    Args:
        v: The content to validate

   ...
2) failure-recovery-system/cicd_integration.py:118 — failure-recovery-system.cicd_integration.CICDEvent.__post_init__ (score 0.18)
   Evidence: Score 0.18, method: __post_init__
3) failure-recovery-system/cicd_integration.py:158 — failure-recovery-system.cicd_integration.RecoveryResponse.__post_init__ (score 0.18)
   Evidence: Score 0.18, method: __post_init__
4) failure-recovery-system/cicd_integration.py:170 — failure-recovery-system.cicd_integration.WebhookSecurityValidator.__init__ (score 0.18)
   Evidence: Score 0.18, method: __init__
5) failure-recovery-system/cicd_integration.py:173 — failure-recovery-system.cicd_integration.WebhookSecurityValidator.validate_github_signature (score 0.18)
   Evidence: Score 0.18, Validate GitHub webhook signature.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToToolResults
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->