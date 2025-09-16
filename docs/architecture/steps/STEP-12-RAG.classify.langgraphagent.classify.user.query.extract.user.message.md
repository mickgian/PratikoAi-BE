# RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message (RAG.classify.langgraphagent.classify.user.query.extract.user.message)

**Type:** process  
**Category:** classify  
**Node ID:** `ExtractQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractQuery` (LangGraphAgent._classify_user_query Extract user message).

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
  `RAG STEP 12 (RAG.classify.langgraphagent.classify.user.query.extract.user.message): LangGraphAgent._classify_user_query Extract user message | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.39

Top candidates:
1) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each domain
2) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.39)
   Evidence: Score 0.39, Calculate confidence scores for each action
3) app/services/ccnl_integration_service.py:163 — app.services.ccnl_integration_service.CCNLIntegrationService._extract_ccnl_parameters (score 0.37)
   Evidence: Score 0.37, Extract parameters for CCNL tool from user query and classification.

Args:
    ...
4) app/services/domain_prompt_templates.py:29 — app.services.domain_prompt_templates.PromptTemplateManager._load_templates (score 0.37)
   Evidence: Score 0.37, Load all domain-action prompt template combinations
5) app/services/domain_prompt_templates.py:355 — app.services.domain_prompt_templates.PromptTemplateManager.get_prompt (score 0.37)
   Evidence: Score 0.37, Get the appropriate prompt for domain-action combination.

RAG STEP 43 — PromptT...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->