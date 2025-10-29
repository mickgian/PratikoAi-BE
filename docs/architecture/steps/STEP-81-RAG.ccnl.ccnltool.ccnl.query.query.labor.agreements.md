# RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLQuery` (CCNLTool.ccnl_query Query labor agreements).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/ccnl.py:14` - `step_81__ccnlquery()`
- **Role:** Node
- **Status:** ✅
- **Behavior notes:** Thin async orchestrator that executes on-demand CCNL (Italian Collective Labor Agreement) queries when the LLM calls the CCNLTool. Uses CCNLTool for querying labor agreements, salary calculations, leave entitlements, and compliance information. Routes to Step 99 (ToolResults). Note: Mermaid shows CCNLQuery → PostgresQuery → CCNLCalc → ToolResults, but implementation collapses internal steps as CCNLTool handles PostgreSQL queries and calculations internally.

## Differences (Blueprint vs Current)
- Mermaid diagram shows intermediate steps (PostgresQuery and CCNLCalc) but implementation collapses these into CCNLTool's internal logic - this is acceptable as the orchestrator provides the same external behavior

## Risks / Impact
- None - uses existing CCNLTool infrastructure with comprehensive test coverage

## TDD Task List
- [x] Unit tests (CCNL query execution, search queries, salary calculation, leave calculation, metadata, routing, context preservation, error handling)
- [x] Integration tests (Step 79→81→99 flow, Step 99 preparation)
- [x] Implementation changes (thin async orchestrator wrapping CCNLTool)
- [x] Observability: add structured log line
  `RAG STEP 81 (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements): CCNLTool.ccnl_query Query labor agreements | attrs={...}`
- [x] Feature flag / config if needed (uses existing CCNLTool configuration)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_81
- Incoming edges: [79]
- Outgoing edges: [99]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->