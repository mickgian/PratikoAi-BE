# RAG STEP 126 — Determine action (RAG.platform.determine.action)

**Type:** process  
**Category:** platform  
**Node ID:** `DetermineAction`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DetermineAction` (Determine action).

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
  `RAG STEP 126 (RAG.platform.determine.action): Determine action | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/platform.py:2723 — app.orchestrators.platform.step_126__determine_action (score 0.31)
   Evidence: Score 0.31, RAG STEP 126 — Determine action
ID: RAG.platform.determine.action
Type: process ...
2) app/orchestrators/streaming.py:80 — app.orchestrators.streaming._determine_streaming_preference (score 0.27)
   Evidence: Score 0.27, Determine if streaming is requested based on various sources.

Priority order:
1...
3) app/models/cassazione.py:311 — app.models.cassazione.determine_related_sectors (score 0.27)
   Evidence: Score 0.27, Determine which CCNL sectors are related to a legal decision.
4) app/services/document_processor.py:501 — app.services.document_processor.DocumentProcessor._determine_document_type (score 0.27)
   Evidence: Score 0.27, Determine document type from URL.

Args:
    document_url: Document URL
    
Ret...
5) app/services/domain_action_classifier.py:68 — app.services.domain_action_classifier.DomainActionClassifier.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->