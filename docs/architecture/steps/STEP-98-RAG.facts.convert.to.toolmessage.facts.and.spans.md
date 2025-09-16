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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/services/knowledge_search_service.py:377 — app.services.knowledge_search_service.KnowledgeSearchService._combine_and_deduplicate_results (score 0.27)
   Evidence: Score 0.27, Combine results from BM25 and vector search, removing duplicates.
2) app/ragsteps/facts/step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts.py:34 — app.ragsteps.facts.step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts.step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts (score 0.26)
   Evidence: Score 0.26, function: step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts
3) app/ragsteps/facts/step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts.py:22 — app.ragsteps.facts.step_40_rag_facts_contextbuilder_merge_facts_and_kb_docs_and_optional_doc_facts.run (score 0.26)
   Evidence: Score 0.26, function: run
4) evals/helpers.py:129 — evals.helpers.process_trace_results (score 0.25)
   Evidence: Score 0.25, Process results for a single trace.

Args:
    report: The report dictionary.
  ...
5) app/api/v1/ccnl_search.py:490 — app.api.v1.ccnl_search._convert_search_response (score 0.25)
   Evidence: Score 0.25, Convert internal SearchResponse to API model.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToToolResults
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->