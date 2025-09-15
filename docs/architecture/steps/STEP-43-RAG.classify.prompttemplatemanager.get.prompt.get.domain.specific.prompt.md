# RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt)

**Type:** process  
**Category:** classify  
**Node ID:** `DomainPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DomainPrompt` (PromptTemplateManager.get_prompt Get domain-specific prompt).

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
  `RAG STEP 43 (RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt): PromptTemplateManager.get_prompt Get domain-specific prompt | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.43

Top candidates:
1) app/services/domain_prompt_templates.py:346 — app.services.domain_prompt_templates.PromptTemplateManager.get_prompt (score 0.43)
   Evidence: Score 0.43, Get the appropriate prompt for domain-action combination.

Args:
    domain: Pro...
2) app/services/domain_prompt_templates.py:20 — app.services.domain_prompt_templates.PromptTemplateManager._load_templates (score 0.41)
   Evidence: Score 0.41, Load all domain-action prompt template combinations
3) app/services/domain_prompt_templates.py:430 — app.services.domain_prompt_templates.PromptTemplateManager.get_available_combinations (score 0.41)
   Evidence: Score 0.41, Get all available domain-action combinations
4) app/services/domain_prompt_templates.py:14 — app.services.domain_prompt_templates.PromptTemplateManager (score 0.36)
   Evidence: Score 0.36, Manages domain-action specific prompt templates for Italian professionals
5) app/core/langgraph/graph.py:345 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.35)
   Evidence: Score 0.35, Get the appropriate system prompt based on classification.

Args:
    messages: ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->