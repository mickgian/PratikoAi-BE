# RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt)

**Type:** process  
**Category:** classify  
**Node ID:** `DomainPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DomainPrompt` (PromptTemplateManager.get_prompt Get domain-specific prompt).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ✅ Implemented
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
  `RAG STEP 43 (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt): PromptTemplateManager.get_prompt Get domain-specific prompt | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.47

Top candidates:
1) app/services/domain_prompt_templates.py:355 — app.services.domain_prompt_templates.PromptTemplateManager.get_prompt (score 0.47)
   Evidence: Score 0.47, Get the appropriate prompt for domain-action combination.

RAG STEP 43 — PromptT...
2) app/orchestrators/classify.py:210 — app.orchestrators.classify.step_31__classify_domain (score 0.46)
   Evidence: Score 0.46, RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
ID: RAG....
3) app/services/domain_prompt_templates.py:479 — app.services.domain_prompt_templates.PromptTemplateManager.get_available_combinations (score 0.46)
   Evidence: Score 0.46, Get all available domain-action combinations
4) app/services/domain_prompt_templates.py:29 — app.services.domain_prompt_templates.PromptTemplateManager._load_templates (score 0.44)
   Evidence: Score 0.44, Load all domain-action prompt template combinations
5) app/orchestrators/classify.py:544 — app.orchestrators.classify.step_35__llmfallback (score 0.44)
   Evidence: Score 0.44, RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
ID: RA...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->