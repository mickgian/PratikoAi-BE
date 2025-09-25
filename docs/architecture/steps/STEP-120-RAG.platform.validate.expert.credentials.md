# RAG STEP 120 — Validate expert credentials (RAG.platform.validate.expert.credentials)

**Type:** process  
**Category:** platform  
**Node ID:** `ValidateExpert`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateExpert` (Validate expert credentials).

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
  `RAG STEP 120 (RAG.platform.validate.expert.credentials): Validate expert credentials | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/orchestrators/platform.py:2705 — app.orchestrators.platform.step_120__validate_expert (score 0.30)
   Evidence: Score 0.30, RAG STEP 120 — Validate expert credentials
ID: RAG.platform.validate.expert.cred...
2) app/services/expert_feedback_collector.py:149 — app.services.expert_feedback_collector.ExpertFeedbackCollector._validate_feedback_data (score 0.30)
   Evidence: Score 0.30, Validate feedback data structure and content
3) app/services/expert_validation_workflow.py:371 — app.services.expert_validation_workflow.ExpertValidationWorkflow._calculate_credentials_score (score 0.29)
   Evidence: Score 0.29, Calculate score based on professional credentials
4) app/services/expert_validation_workflow.py:430 — app.services.expert_validation_workflow.ExpertValidationWorkflow._validate_regulatory_references (score 0.29)
   Evidence: Score 0.29, Validate regulatory references for accuracy and currency
5) validate_italian_implementation.py:37 — validate_italian_implementation.main (score 0.27)
   Evidence: Score 0.27, Validate Italian Knowledge Base implementation.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ValidateExpert
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->