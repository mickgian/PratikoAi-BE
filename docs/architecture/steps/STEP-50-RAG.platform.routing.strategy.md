# RAG STEP 50 — Routing strategy? (RAG.platform.routing.strategy)

**Type:** decision  
**Category:** platform  
**Node ID:** `StrategyType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StrategyType` (Routing strategy?).

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
  `RAG STEP 50 (RAG.platform.routing.strategy): Routing strategy? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.18

Top candidates:
1) failure-recovery-system/decision_tree_engine.py:207 — failure-recovery-system.decision_tree_engine.RecoveryStrategy.__post_init__ (score 0.18)
   Evidence: Score 0.18, method: __post_init__
2) app/models/cassazione_data.py:367 — app.models.cassazione_data.ScrapingError.category (score 0.18)
   Evidence: Score 0.18, Categorize the error.
3) app/services/export_file_generator.py:792 — app.services.export_file_generator.ExportFileGenerator._translate_query_type (score 0.18)
   Evidence: Score 0.18, Translate query type to Italian
4) failure-recovery-system/recovery_orchestrator.py:879 — failure-recovery-system.recovery_orchestrator.RecoveryOrchestrator._get_strategy_by_id (score 0.17)
   Evidence: Score 0.17, Get a strategy by its ID from all available strategies.
5) app/models/cassazione_data.py:319 — app.models.cassazione_data.ScrapingStatistics.save_rate (score 0.17)
   Evidence: Score 0.17, Calculate decision save rate.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for StrategyType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->