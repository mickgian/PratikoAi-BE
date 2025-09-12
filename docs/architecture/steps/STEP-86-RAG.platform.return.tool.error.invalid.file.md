# RAG STEP 86 — Return tool error Invalid file (RAG.platform.return.tool.error.invalid.file)

**Type:** error  
**Category:** platform  
**Node ID:** `ToolErr`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolErr` (Return tool error Invalid file).

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
  `RAG STEP 86 (RAG.platform.return.tool.error.invalid.file): Return tool error Invalid file | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.15

Top candidates:
1) app/core/langgraph/tools/__init__.py:1 — app.core.langgraph.tools.__init__ (score 0.15)
   Evidence: Score 0.15, LangGraph tools for enhanced language model capabilities.

This package contains...
2) app/core/langgraph/tools/ccnl_tool.py:1 — app.core.langgraph.tools.ccnl_tool (score 0.15)
   Evidence: Score 0.15, CCNL Integration Tool for LangGraph.

This tool enables the LLM to access Italia...
3) app/core/langgraph/tools/ccnl_tool.py:29 — app.core.langgraph.tools.ccnl_tool.CCNLQueryInput (score 0.15)
   Evidence: Score 0.15, Input schema for CCNL queries.
4) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.15)
   Evidence: Score 0.15, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.
5) app/core/langgraph/tools/ccnl_tool.py:83 — app.core.langgraph.tools.ccnl_tool.CCNLTool.__init__ (score 0.15)
   Evidence: Score 0.15, method: __init__

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for ToolErr
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->