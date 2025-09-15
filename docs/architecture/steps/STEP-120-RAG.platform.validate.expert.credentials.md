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
Status: ❌  |  Confidence: 0.20

Top candidates:
1) app/services/validators/financial_validation_engine.py:187 — app.services.validators.financial_validation_engine.FinancialValidationEngine.__init__ (score 0.20)
   Evidence: Score 0.20, Initialize the Financial Validation Engine.

Args:
    config: Engine configurat...
2) app/services/validators/financial_validation_engine.py:209 — app.services.validators.financial_validation_engine.FinancialValidationEngine._initialize_components (score 0.20)
   Evidence: Score 0.20, Initialize all validation components based on configuration.
3) app/services/validators/financial_validation_engine.py:273 — app.services.validators.financial_validation_engine.FinancialValidationEngine.is_ready (score 0.20)
   Evidence: Score 0.20, Check if the engine is ready to process requests.
4) app/services/validators/financial_validation_engine.py:285 — app.services.validators.financial_validation_engine.FinancialValidationEngine.supported_task_types (score 0.20)
   Evidence: Score 0.20, Get list of supported task types based on enabled modules.
5) app/services/validators/financial_validation_engine.py:302 — app.services.validators.financial_validation_engine.FinancialValidationEngine.execute_single_task (score 0.20)
   Evidence: Score 0.20, Execute a single validation task.

Args:
    task: The validation task to execut...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ValidateExpert
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->