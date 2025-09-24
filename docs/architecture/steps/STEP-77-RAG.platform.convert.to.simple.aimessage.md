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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/platform.py:1782 — app.orchestrators.platform.step_76__convert_aimsg (score 0.30)
   Evidence: Score 0.30, RAG STEP 76 — Convert to AIMessage with tool_calls
ID: RAG.platform.convert.to.a...
2) app/orchestrators/platform.py:1905 — app.orchestrators.platform.step_77__simple_aimsg (score 0.30)
   Evidence: Score 0.30, RAG STEP 77 — Convert to simple AIMessage
ID: RAG.platform.convert.to.simple.aim...
3) app/models/document_simple.py:126 — app.models.document_simple.Document.__init__ (score 0.26)
   Evidence: Score 0.26, method: __init__
4) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.26)
   Evidence: Score 0.26, Check if document has expired
5) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.26)
   Evidence: Score 0.26, Convert document to dictionary for API responses

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for SimpleAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->