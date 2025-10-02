# RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `BuildContext`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `BuildContext` (ContextBuilder.merge facts and KB docs and optional doc facts).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:271` - `step_40__build_context()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator merging canonical facts, KB search results, and optional document facts into unified context. Uses ContextBuilderMerge service for token budget management, content prioritization, and deduplication. Routes to Step 41 (SelectPrompt) with enriched context.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (all sources merge, facts+KB only, token budget, prioritization weights, empty inputs, deduplication, error handling, structured logging)
- [x] Integration tests (end-to-end context merging scenarios with realistic data)
- [x] Implementation changes (ContextBuilderMerge class, merge logic, priority scoring, deduplication, token management)
- [x] Observability: add structured log line  
  `RAG STEP 40 (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts): ContextBuilder.merge facts and KB docs and optional doc facts | attrs={token_count, max_tokens, source_distribution, context_quality_score, deduplication_applied, content_truncated, processing_stage}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.31

Top candidates:
1) app/services/context_builder_merge.py:66 — app.services.context_builder_merge.ContextBuilderMerge.merge_context (score 0.31)
   Evidence: Score 0.31, Merge facts, KB docs, and optional document facts into unified context.

Args:
 ...
2) app/services/context_builder_merge.py:572 — app.services.context_builder_merge.merge_context (score 0.31)
   Evidence: Score 0.31, Convenience function to merge context from facts, KB docs, and document facts.

...
3) app/orchestrators/facts.py:271 — app.orchestrators.facts.step_40__build_context (score 0.30)
   Evidence: Score 0.30, RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts
ID: ...
4) app/services/context_builder_merge.py:53 — app.services.context_builder_merge.ContextBuilderMerge.__init__ (score 0.30)
   Evidence: Score 0.30, method: __init__
5) app/services/context_builder_merge.py:218 — app.services.context_builder_merge.ContextBuilderMerge._create_context_parts (score 0.29)
   Evidence: Score 0.29, Convert inputs to ContextPart objects.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->