# RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt)

**Type:** process  
**Category:** classify  
**Node ID:** `DomainPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DomainPrompt` (PromptTemplateManager.get_prompt Get domain-specific prompt).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/classify.py:831` - `step_43__domain_prompt()`
- **Status:** 🔌
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
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->