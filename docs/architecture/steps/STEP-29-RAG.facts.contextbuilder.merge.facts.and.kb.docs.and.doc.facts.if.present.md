# RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present)

**Type:** process  
**Category:** facts  
**Node ID:** `PreContextFromGolden`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PreContextFromGolden` (ContextBuilder.merge facts and KB docs and doc facts if present).

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
  `RAG STEP 29 (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present): ContextBuilder.merge facts and KB docs and doc facts if present | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.33

Top candidates:
1) app/orchestrators/facts.py:68 — app.orchestrators.facts.step_29__pre_context_from_golden (score 0.33)
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