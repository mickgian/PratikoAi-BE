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
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/facts.py:421 — app.orchestrators.facts.step_98__to_tool_results (score 0.31)
   Evidence: Score 0.31, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...
2) app/orchestrators/platform.py:2245 — app.orchestrators.platform.step_99__tool_results (score 0.28)
   Evidence: Score 0.28, RAG STEP 99 — Return to tool caller
ID: RAG.platform.return.to.tool.caller
Type:...
3) app/services/knowledge_search_service.py:377 — app.services.knowledge_search_service.KnowledgeSearchService._combine_and_deduplicate_results (score 0.27)
   Evidence: Score 0.27, Combine results from BM25 and vector search, removing duplicates.
4) app/orchestrators/facts.py:14 — app.orchestrators.facts.step_14__extract_facts (score 0.25)
   Evidence: Score 0.25, RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts
ID: RAG.facts.at...
5) app/orchestrators/facts.py:32 — app.orchestrators.facts.step_16__canonicalize_facts (score 0.25)
   Evidence: Score 0.25, RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates
ID...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->