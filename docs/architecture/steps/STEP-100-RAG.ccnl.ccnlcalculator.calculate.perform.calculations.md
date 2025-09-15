# RAG STEP 100 — CCNLCalculator.calculate Perform calculations (RAG.ccnl.ccnlcalculator.calculate.perform.calculations)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLCalc`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLCalc` (CCNLCalculator.calculate Perform calculations).

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
  `RAG STEP 100 (RAG.ccnl.ccnlcalculator.calculate.perform.calculations): CCNLCalculator.calculate Perform calculations | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.38

Top candidates:
1) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.38)
   Evidence: Score 0.38, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agree...
2) app/models/ccnl_database.py:103 — app.models.ccnl_database.CCNLAgreementDB.is_currently_valid (score 0.32)
   Evidence: Score 0.32, Check if CCNL agreement is currently valid.
3) app/services/ccnl_change_detector.py:291 — app.services.ccnl_change_detector.CCNLChangeDetector.detect_structural_changes (score 0.30)
   Evidence: Score 0.30, Detect structural changes in CCNL agreement.
4) app/services/ccnl_calculator_engine.py:233 — app.services.ccnl_calculator_engine.EnhancedCCNLCalculator (score 0.29)
   Evidence: Score 0.29, Enhanced CCNL calculator with comprehensive calculation capabilities.
5) app/services/ccnl_service.py:806 — app.services.ccnl_service.CCNLService._convert_external_data_to_agreement (score 0.29)
   Evidence: Score 0.29, Convert external data format to CCNLAgreement.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->