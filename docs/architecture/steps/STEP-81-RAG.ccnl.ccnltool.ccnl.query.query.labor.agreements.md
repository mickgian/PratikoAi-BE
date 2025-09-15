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
Status: 🔌  |  Confidence: 0.41

Top candidates:
1) app/core/langgraph/tools/ccnl_tool.py:64 — app.core.langgraph.tools.ccnl_tool.CCNLTool (score 0.41)
   Evidence: Score 0.41, LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data.
2) app/models/ccnl_data.py:715 — app.models.ccnl_data.CCNLCalculator.__init__ (score 0.41)
   Evidence: Score 0.41, Initialize calculator with CCNL agreement.
3) app/core/langgraph/tools/ccnl_tool.py:101 — app.core.langgraph.tools.ccnl_tool.CCNLTool._run (score 0.36)
   Evidence: Score 0.36, Execute CCNL query (synchronous version).
4) app/models/ccnl_database.py:103 — app.models.ccnl_database.CCNLAgreementDB.is_currently_valid (score 0.35)
   Evidence: Score 0.35, Check if CCNL agreement is currently valid.
5) app/services/ccnl_service.py:806 — app.services.ccnl_service.CCNLService._convert_external_data_to_agreement (score 0.34)
   Evidence: Score 0.34, Convert external data format to CCNLAgreement.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->