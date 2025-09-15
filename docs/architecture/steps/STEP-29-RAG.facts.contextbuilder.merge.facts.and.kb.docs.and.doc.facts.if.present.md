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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/services/context_builder.py:459 — app.services.context_builder.MultiSourceContextBuilder._estimate_length_from_tokens (score 0.27)
   Evidence: Score 0.27, Estimate character length from token count
2) app/services/context_builder.py:56 — app.services.context_builder.MultiSourceContextBuilder.__init__ (score 0.26)
   Evidence: Score 0.26, method: __init__
3) app/services/context_builder.py:179 — app.services.context_builder.MultiSourceContextBuilder._group_results_by_source (score 0.26)
   Evidence: Score 0.26, Group search results by source type
4) app/services/context_builder.py:395 — app.services.context_builder.MultiSourceContextBuilder._clean_excerpt (score 0.26)
   Evidence: Score 0.26, Clean and improve excerpt boundaries
5) app/services/context_builder.py:437 — app.services.context_builder.MultiSourceContextBuilder._split_sentences (score 0.26)
   Evidence: Score 0.26, Split text into sentences (Italian-aware)

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for PreContextFromGolden
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->