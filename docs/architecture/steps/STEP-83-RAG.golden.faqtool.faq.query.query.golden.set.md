# RAG STEP 83 — FAQTool.faq_query Query Golden Set (RAG.golden.faqtool.faq.query.query.golden.set)

**Type:** process  
**Category:** golden  
**Node ID:** `FAQQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FAQQuery` (FAQTool.faq_query Query Golden Set).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_83__faqquery`, `app/core/langgraph/tools/faq_tool.py:FAQTool`
- **Role:** Node
- **Status:** missing
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
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Confidence: 0.54

Top candidates:
1) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.54)
   Evidence: Score 0.54, Query the FAQ system with semantic search and response variation.

This endpoint...
2) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.54)
   Evidence: Score 0.54, Approve, reject, or request revision for a generated FAQ
3) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.54)
   Evidence: Score 0.54, Publish an approved FAQ to make it available to users
4) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
5) app/api/v1/faq_automation.py:281 — app.api.v1.faq_automation.analyze_query_patterns (score 0.51)
   Evidence: Score 0.51, Trigger analysis of query patterns to identify new FAQ candidates

Notes:
- Strong implementation match found
- Wired via graph registry ✅
- Incoming: [79], Outgoing: [99]

Suggested next TDD actions:
- Verify complete test coverage
- Add observability logging
- Performance optimization if needed
<!-- AUTO-AUDIT:END -->