# RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present)

**Type:** process  
**Category:** facts  
**Node ID:** `PreContextFromGolden`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PreContextFromGolden` (ContextBuilder.merge facts and KB docs and doc facts if present).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/facts.py:step_29__pre_context_from_golden`
- **Role:** Internal
- **Status:** missing
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (golden+KB merge, atomic facts, optional document facts, empty KB deltas, routing, context preservation)
- [x] Integration tests (KBDelta=Yes path, context preservation for Step 39)
- [x] Implementation changes (thin async orchestrator wrapping ContextBuilderMerge service)
- [x] Observability: add structured log line
  `RAG STEP 29 (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present): ContextBuilder.merge facts and KB docs and doc facts if present | attrs={...}`
- [x] Feature flag / config if needed (uses existing ContextBuilderMerge configuration)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.33

Top candidates:
1) app/orchestrators/facts.py:189 — app.orchestrators.facts.step_29__pre_context_from_golden (score 0.33)
   Evidence: Score 0.33, RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present
ID...
2) app/services/context_builder_merge.py:66 — app.services.context_builder_merge.ContextBuilderMerge.merge_context (score 0.29)
   Evidence: Score 0.29, Merge facts, KB docs, and optional document facts into unified context.

Args:
 ...
3) app/services/context_builder_merge.py:572 — app.services.context_builder_merge.merge_context (score 0.29)
   Evidence: Score 0.29, Convenience function to merge context from facts, KB docs, and document facts.

...
4) app/services/context_builder_merge.py:53 — app.services.context_builder_merge.ContextBuilderMerge.__init__ (score 0.29)
   Evidence: Score 0.29, method: __init__
5) app/services/context_builder_merge.py:218 — app.services.context_builder_merge.ContextBuilderMerge._create_context_parts (score 0.28)
   Evidence: Score 0.28, Convert inputs to ContextPart objects.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->