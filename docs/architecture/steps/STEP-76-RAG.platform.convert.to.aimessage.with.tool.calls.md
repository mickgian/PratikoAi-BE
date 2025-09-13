# RAG STEP 76 — Convert to AIMessage with tool_calls (RAG.platform.convert.to.aimessage.with.tool.calls)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertAIMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertAIMsg` (Convert to AIMessage with tool_calls).

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
  `RAG STEP 76 (RAG.platform.convert.to.aimessage.with.tool.calls): Convert to AIMessage with tool_calls | attrs={...}`
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
2) app/core/langgraph/tools/ccnl_tool.py:83 — app.core.langgraph.tools.ccnl_tool.CCNLTool.__init__ (score 0.24)
   Evidence: Score 0.24, method: __init__
3) app/core/langgraph/tools/ccnl_tool.py:90 — app.core.langgraph.tools.ccnl_tool.CCNLTool.search_service (score 0.24)
   Evidence: Score 0.24, method: search_service
4) app/core/langgraph/tools/ccnl_tool.py:96 — app.core.langgraph.tools.ccnl_tool.CCNLTool.calculator_engine (score 0.24)
   Evidence: Score 0.24, method: calculator_engine
5) app/core/langgraph/tools/ccnl_tool.py:101 — app.core.langgraph.tools.ccnl_tool.CCNLTool._run (score 0.24)
   Evidence: Score 0.24, Execute CCNL query (synchronous version).

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertAIMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->