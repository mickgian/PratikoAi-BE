# RAG STEP 33 — Confidence at least threshold? (RAG.classify.confidence.at.least.threshold)

**Type:** process  
**Category:** classify  
**Node ID:** `ConfidenceCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConfidenceCheck` (Confidence at least threshold?).

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
  `RAG STEP 33 (RAG.classify.confidence.at.least.threshold): Confidence at least threshold? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.44

Top candidates:
1) app/orchestrators/classify.py:542 — app.orchestrators.classify.step_35__llmfallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...
2) app/orchestrators/classify.py:829 — app.orchestrators.classify.step_43__domain_prompt (score 0.40)
   Evidence: Score 0.40, RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt
ID: RA...
3) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.40)
   Evidence: Score 0.40, Calculate confidence scores for each domain
4) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.40)
   Evidence: Score 0.40, Calculate confidence scores for each action
5) app/services/domain_prompt_templates.py:29 — app.services.domain_prompt_templates.PromptTemplateManager._load_templates (score 0.37)
   Evidence: Score 0.37, Load all domain-action prompt template combinations

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->