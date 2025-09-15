# RAG STEP 15 — Continue without classification (RAG.prompting.continue.without.classification)

**Type:** process  
**Category:** prompting  
**Node ID:** `DefaultPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DefaultPrompt` (Continue without classification).

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
  `RAG STEP 15 (RAG.prompting.continue.without.classification): Continue without classification | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.19

Top candidates:
1) app/core/monitoring/metrics.py:612 — app.core.monitoring.metrics.track_classification_usage (score 0.19)
   Evidence: Score 0.19, Track domain-action classification usage and metrics.
    
    Args:
        dom...
2) app/services/ccnl_rss_monitor.py:358 — app.services.ccnl_rss_monitor.CCNLUpdateDetector.classify_sector (score 0.19)
   Evidence: Score 0.19, Classify which CCNL sector an update refers to.
3) app/core/langgraph/graph.py:681 — app.core.langgraph.graph.LangGraphAgent._should_continue (score 0.18)
   Evidence: Score 0.18, Determine if the agent should continue or end based on the last message.

Args:
...
4) app/models/cassazione.py:244 — app.models.cassazione.extract_legal_keywords (score 0.18)
   Evidence: Score 0.18, Extract legal keywords from decision text.
5) app/models/cassazione.py:261 — app.models.cassazione.classify_precedent_value (score 0.18)
   Evidence: Score 0.18, Classify the precedent value of a Cassazione decision.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DefaultPrompt
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->