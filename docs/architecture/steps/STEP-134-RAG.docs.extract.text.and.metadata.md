# RAG STEP 134 — Extract text and metadata (RAG.docs.extract.text.and.metadata)

**Type:** process  
**Category:** docs  
**Node ID:** `ParseDocs`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ParseDocs` (Extract text and metadata).

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
  `RAG STEP 134 (RAG.docs.extract.text.and.metadata): Extract text and metadata | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.23

Top candidates:
1) app/services/italian_document_collector.py:451 — app.services.italian_document_collector.ItalianDocumentCollector._extract_keywords (score 0.23)
   Evidence: Score 0.23, Extract relevant keywords from document content.
2) app/services/italian_document_collector.py:440 — app.services.italian_document_collector.ItalianDocumentCollector._extract_tax_types (score 0.22)
   Evidence: Score 0.22, Extract relevant tax types from document content.
3) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.22)
   Evidence: Score 0.22, Check if document has expired
4) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.22)
   Evidence: Score 0.22, Convert document to dictionary for API responses
5) app/services/legal_document_analyzer.py:950 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_key_clauses (score 0.22)
   Evidence: Score 0.22, Extract important contract clauses

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ParseDocs
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->