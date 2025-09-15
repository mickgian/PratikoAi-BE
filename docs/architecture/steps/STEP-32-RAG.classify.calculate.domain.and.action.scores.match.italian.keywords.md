# RAG STEP 32 — Calculate domain and action scores Match Italian keywords (RAG.classify.calculate.domain.and.action.scores.match.italian.keywords)

**Type:** process  
**Category:** classify  
**Node ID:** `CalcScores`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CalcScores` (Calculate domain and action scores Match Italian keywords).

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
  `RAG STEP 32 (RAG.classify.calculate.domain.and.action.scores.match.italian.keywords): Calculate domain and action scores Match Italian keywords | attrs={...}`
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
1) app/services/domain_action_classifier.py:416 — app.services.domain_action_classifier.DomainActionClassifier._calculate_domain_scores (score 0.43)
   Evidence: Score 0.43, Calculate confidence scores for each domain
2) app/services/domain_action_classifier.py:447 — app.services.domain_action_classifier.DomainActionClassifier._calculate_action_scores (score 0.43)
   Evidence: Score 0.43, Calculate confidence scores for each action
3) app/services/domain_prompt_templates.py:20 — app.services.domain_prompt_templates.PromptTemplateManager._load_templates (score 0.37)
   Evidence: Score 0.37, Load all domain-action prompt template combinations
4) app/services/domain_prompt_templates.py:346 — app.services.domain_prompt_templates.PromptTemplateManager.get_prompt (score 0.37)
   Evidence: Score 0.37, Get the appropriate prompt for domain-action combination.

Args:
    domain: Pro...
5) app/services/domain_prompt_templates.py:430 — app.services.domain_prompt_templates.PromptTemplateManager.get_available_combinations (score 0.37)
   Evidence: Score 0.37, Get all available domain-action combinations

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->