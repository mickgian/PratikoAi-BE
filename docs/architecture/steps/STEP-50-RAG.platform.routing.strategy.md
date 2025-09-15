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
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/core/langgraph/graph.py:458 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.28)
   Evidence: Score 0.28, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...
2) app/schemas/privacy.py:191 — app.schemas.privacy.validate_consent_type (score 0.26)
   Evidence: Score 0.26, Validate consent type string.
3) app/schemas/privacy.py:221 — app.schemas.privacy.validate_pii_type (score 0.26)
   Evidence: Score 0.26, Validate PII type string.
4) app/services/document_processor.py:501 — app.services.document_processor.DocumentProcessor._determine_document_type (score 0.26)
   Evidence: Score 0.26, Determine document type from URL.

Args:
    document_url: Document URL
    
Ret...
5) failure-recovery-system/failure_categorizer.py:655 — failure-recovery-system.failure_categorizer.FailureCategorizer._identify_failure_type (score 0.26)
   Evidence: Score 0.26, Identify the primary failure type using pattern matching.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for StrategyType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->