# RAG STEP 106 — Create async generator (RAG.platform.create.async.generator)

**Type:** process  
**Category:** platform  
**Node ID:** `AsyncGen`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AsyncGen` (Create async generator).

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
  `RAG STEP 106 (RAG.platform.create.async.generator): Create async generator | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/models/ccnl_data.py:813 — app.models.ccnl_data.create_ccnl_id (score 0.26)
   Evidence: Score 0.26, Create standardized CCNL ID.
2) app/core/database.py:10 — app.core.database.get_async_session (score 0.26)
   Evidence: Score 0.26, Get async database session.
3) app/models/regulatory_documents.py:310 — app.models.regulatory_documents.create_document_id (score 0.26)
   Evidence: Score 0.26, Create standardized document ID.

Args:
    source: Source authority
    documen...
4) app/services/export_file_generator.py:29 — app.services.export_file_generator.ExportFileGenerator.__init__ (score 0.26)
   Evidence: Score 0.26, method: __init__
5) app/services/vector_service.py:112 — app.services.vector_service.VectorService.create_embedding (score 0.26)
   Evidence: Score 0.26, Create embedding vector for text.

Args:
    text: Text to embed
    
Returns:
 ...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AsyncGen
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->