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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/models/cassazione.py:311 — app.models.cassazione.determine_related_sectors (score 0.27)
   Evidence: Score 0.27, Determine which CCNL sectors are related to a legal decision.
2) app/services/document_processor.py:501 — app.services.document_processor.DocumentProcessor._determine_document_type (score 0.27)
   Evidence: Score 0.27, Determine document type from URL.

Args:
    document_url: Document URL
    
Ret...
3) app/services/domain_action_classifier.py:68 — app.services.domain_action_classifier.DomainActionClassifier.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__
4) app/services/knowledge_integrator.py:519 — app.services.knowledge_integrator.KnowledgeIntegrator._determine_knowledge_category (score 0.27)
   Evidence: Score 0.27, Determine knowledge category based on document data.

Args:
    document_data: D...
5) app/services/knowledge_integrator.py:556 — app.services.knowledge_integrator.KnowledgeIntegrator._determine_knowledge_subcategory (score 0.27)
   Evidence: Score 0.27, Determine knowledge subcategory.

Args:
    document_data: Document information
...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DetermineAction
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->