# RAG STEP 88 — DocClassifier.classify Detect document type (RAG.classify.docclassifier.classify.detect.document.type)

**Type:** process  
**Category:** classify  
**Node ID:** `DocClassify`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocClassify` (DocClassifier.classify Detect document type).

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
  `RAG STEP 88 (RAG.classify.docclassifier.classify.detect.document.type): DocClassifier.classify Detect document type | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.46

Top candidates:
1) app/orchestrators/classify.py:208 — app.orchestrators.classify.step_31__classify_domain (score 0.46)
   Evidence: Score 0.46, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
2) app/orchestrators/classify.py:542 — app.orchestrators.classify.step_35__llmfallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
3) app/orchestrators/classify.py:315 — app.orchestrators.classify.step_32__calc_scores (score 0.43)
   Evidence: Score 0.43, RAG STEP 32 — Calculate domain and action scores Match Italian keywords
ID: RAG....
4) app/orchestrators/classify.py:675 — app.orchestrators.classify.step_35__llm_fallback (score 0.43)
   Evidence: Score 0.43, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
5) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.42)
   Evidence: Score 0.42, Calculate confidence scores for each domain

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->