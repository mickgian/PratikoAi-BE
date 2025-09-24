# RAG STEP 83 — FAQTool.faq_query Query Golden Set (RAG.golden.faqtool.faq.query.query.golden.set)

**Type:** process  
**Category:** golden  
**Node ID:** `FAQQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FAQQuery` (FAQTool.faq_query Query Golden Set).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_83__faqquery`, `app/core/langgraph/tools/faq_tool.py:FAQTool`
- **Status:** ✅ Implemented
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Top candidates:
1) app/orchestrators/golden.py:122 — app.orchestrators.golden.step_83__faqquery (score 1.00)
   Evidence: Score 1.00, RAG STEP 83 — FAQTool.faq_query Query Golden Set
ID: RAG.golden.faqtool.faq.query.query.golden.set
Type: process
2) app/core/langgraph/tools/faq_tool.py:15 — app.core.langgraph.tools.faq_tool.FAQTool (score 0.95)
   Evidence: Score 0.95, Tool for querying the FAQ/Golden Set with semantic search.
3) app/services/semantic_faq_matcher.py:96 — app.services.semantic_faq_matcher.SemanticFAQMatcher.find_matching_faqs (score 0.90)
   Evidence: Score 0.90, Find semantically matching FAQs with confidence scoring.

Notes:
- ✅ Implementation complete and wired correctly
- ✅ Async orchestrator wrapping FAQTool
- ✅ FAQTool created in LangGraph tools
- ✅ 13/13 tests passing
- ✅ Routes to Step 99 (ToolResults) per Mermaid
- ✅ Uses SemanticFAQMatcher for semantic search
- ✅ Supports confidence-based filtering (low, medium, high, exact)

Completed TDD actions:
- ✅ Created thin async orchestrator in app/orchestrators/golden.py
- ✅ Created FAQTool in app/core/langgraph/tools/faq_tool.py
- ✅ Integrated with SemanticFAQMatcher and IntelligentFAQService
- ✅ Implemented 13 comprehensive tests (unit + parity + integration)
- ✅ Added structured observability logging
- ✅ Verified error handling and edge cases
<!-- AUTO-AUDIT:END -->