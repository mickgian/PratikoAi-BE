# RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `BuildContext`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `BuildContext` (ContextBuilder.merge facts and KB docs and optional doc facts).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:271` - `step_40__build_context()`
- **Status:** 🔌
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
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->