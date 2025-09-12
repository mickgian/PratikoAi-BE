# RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

**Type:** process  
**Category:** response  
**Node ID:** `ToolCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolCheck` (Response has tool_calls?).

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
  `RAG STEP 75 (RAG.response.response.has.tool.calls): Response has tool_calls? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/models/query.py:50 — app.models.query.LLMResponse.__post_init__ (score 0.25)
   Evidence: Score 0.25, Add timestamp if not present.
2) app/models/query.py:74 — app.models.query.QueryResponse.__post_init__ (score 0.24)
   Evidence: Score 0.24, method: __post_init__
3) app/schemas/auth.py:139 — app.schemas.auth.SessionResponse.sanitize_name (score 0.23)
   Evidence: Score 0.23, Sanitize the session name.

Args:
    v: The name to sanitize

Returns:
    str:...
4) app/core/langgraph/tools/ccnl_tool.py:83 — app.core.langgraph.tools.ccnl_tool.CCNLTool.__init__ (score 0.23)
   Evidence: Score 0.23, method: __init__
5) app/core/langgraph/tools/ccnl_tool.py:90 — app.core.langgraph.tools.ccnl_tool.CCNLTool.search_service (score 0.23)
   Evidence: Score 0.23, method: search_service

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToolCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->