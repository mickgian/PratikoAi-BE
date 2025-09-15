# RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `BuildContext`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `BuildContext` (ContextBuilder.merge facts and KB docs and optional doc facts).

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
  `RAG STEP 40 (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts): ContextBuilder.merge facts and KB docs and optional doc facts | attrs={...}`
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
1) app/services/context_builder.py:56 — app.services.context_builder.MultiSourceContextBuilder.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__
2) app/services/context_builder.py:179 — app.services.context_builder.MultiSourceContextBuilder._group_results_by_source (score 0.27)
   Evidence: Score 0.27, Group search results by source type
3) app/services/context_builder.py:395 — app.services.context_builder.MultiSourceContextBuilder._clean_excerpt (score 0.27)
   Evidence: Score 0.27, Clean and improve excerpt boundaries
4) app/services/context_builder.py:437 — app.services.context_builder.MultiSourceContextBuilder._split_sentences (score 0.27)
   Evidence: Score 0.27, Split text into sentences (Italian-aware)
5) app/services/context_builder.py:449 — app.services.context_builder.MultiSourceContextBuilder._count_tokens (score 0.27)
   Evidence: Score 0.27, Estimate token count for text

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for BuildContext
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->