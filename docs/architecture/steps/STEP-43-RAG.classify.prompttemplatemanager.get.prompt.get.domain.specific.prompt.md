# RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt)

**Type:** process  
**Category:** classify  
**Node ID:** `DomainPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DomainPrompt` (PromptTemplateManager.get_prompt Get domain-specific prompt).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/classify.py:831` - `step_43__domain_prompt()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator retrieving domain-specific prompt templates using PromptTemplateManager. Selects appropriate prompt based on classified domain-action pair to enable specialized conversation handling for different domains.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 43 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.47

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
- Implemented (internal) - no wiring required

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->