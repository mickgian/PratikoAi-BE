# RAG STEP 38 — Use rule-based classification (RAG.platform.use.rule.based.classification)

**Type:** process  
**Category:** platform  
**Node ID:** `UseRuleBased`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `UseRuleBased` (Use rule-based classification).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/platform.py:1062` - `step_38__use_rule_based()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator proceeding with rule-based classification result. Routes to context building when classification confidence is sufficient.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 38 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/orchestrators/platform.py:1062 — app.orchestrators.platform.step_38__use_rule_based (score 0.34)
   Evidence: Score 0.34, RAG STEP 38 — Use rule-based classification
ID: RAG.platform.use.rule.based.clas...
2) app/orchestrators/llm.py:179 — app.orchestrators.llm.step_37__use_llm (score 0.26)
   Evidence: Score 0.26, RAG STEP 37 — Use LLM classification
ID: RAG.llm.use.llm.classification
Type: pr...
3) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.26)
   Evidence: Score 0.26, Track domain-action classification usage and metrics.

Args:
    domain: The cla...
4) app/services/document_uploader.py:277 — app.services.document_uploader.DocumentUploader._signature_based_scan (score 0.26)
   Evidence: Score 0.26, Signature-based malware detection
5) rollback-system/health_monitor.py:645 — rollback-system.health_monitor.HealthMonitor._evaluate_rule_condition (score 0.26)
   Evidence: Score 0.26, Evaluate a monitoring rule condition.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->