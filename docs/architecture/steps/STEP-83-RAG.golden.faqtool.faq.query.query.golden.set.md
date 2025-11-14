# RAG STEP 83 — FAQTool.faq_query Query Golden Set (RAG.golden.faqtool.faq.query.query.golden.set)

**Type:** process  
**Category:** golden  
**Node ID:** `FAQQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FAQQuery` (FAQTool.faq_query Query Golden Set).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_83__faqquery`, `app/core/langgraph/tools/faq_tool.py:FAQTool`
- **Role:** Node
- **Status:** ✅
- **Behavior notes:** Thin async orchestrator that executes on-demand FAQ queries when the LLM calls the FAQTool. Uses SemanticFAQMatcher and IntelligentFAQService for semantic FAQ matching with confidence-based filtering (low, medium, high, exact). Supports Italian language queries with concept matching and freshness validation. Routes to Step 99 (ToolResults).

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing SemanticFAQMatcher and IntelligentFAQService infrastructure with comprehensive test coverage

## TDD Task List
- [x] Unit tests (FAQ query execution, tool integration, multiple matches, confidence thresholds, metadata, routing, context preservation, error handling)
- [x] Integration tests (Step 79→83→99 flow, Step 99 preparation)
- [x] Implementation changes (thin async orchestrator wrapping FAQTool)
- [x] Observability: add structured log line
  `RAG STEP 83 (RAG.golden.faqtool.faq.query.query.golden.set): FAQTool.faq_query Query Golden Set | attrs={query, match_count, min_confidence, success, error}`
- [x] Feature flag / config if needed (uses existing FAQ service configuration)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_83
- Incoming edges: [79]
- Outgoing edges: [99]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->