# RAG STEP 81 — CCNLTool.ccnl_query Query labor agreements (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements)

**Type:** process  
**Category:** ccnl  
**Node ID:** `CCNLQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CCNLQuery` (CCNLTool.ccnl_query Query labor agreements).

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
  `RAG STEP 81 (RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements): CCNLTool.ccnl_query Query labor agreements | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.36

Top candidates:
1) app/services/ccnl_calculator_engine.py:1 — app.services.ccnl_calculator_engine (score 0.36)
   Evidence: Score 0.36, CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agree...
2) app/models/ccnl_database.py:103 — app.models.ccnl_database.CCNLAgreementDB.is_currently_valid (score 0.32)
   Evidence: Score 0.32, Check if CCNL agreement is currently valid.
3) app/services/ccnl_service.py:806 — app.services.ccnl_service.CCNLService._convert_external_data_to_agreement (score 0.31)
   Evidence: Score 0.31, Convert external data format to CCNLAgreement.
4) app/data/ccnl_priority1.py:843 — app.data.ccnl_priority1.get_all_priority1_ccnl_data (score 0.30)
   Evidence: Score 0.30, Get all Priority 1 CCNL agreements.
5) app/data/ccnl_priority2.py:1155 — app.data.ccnl_priority2.get_all_priority2_ccnl_data (score 0.30)
   Evidence: Score 0.30, Get all Priority 2 CCNL agreements.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->